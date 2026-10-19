import uuid
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.db import transaction
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .institutional_views import read_authority
from .member_views import localized
from .member_labels import vocabulary as member_vocabulary
from .activity_labels import vocabulary
from .activity_forms import (
    EditorialActivityForm as ActivityForm,
    RegistrationForm,
    DecisionForm,
    CheckinForm,
    EditorialDecisionForm,
    ActivityImageForm,
)
from .models import Activity, ActivityImage, Registration, Attendance, Audit, Document
from .deployment import require_applications_enabled, require_issuance_enabled
from . import services, activity_services, activity_editorial
from .capabilities import allows, restrict_choices


def context(request):
    language, extra = vocabulary(request.GET.get("lang", "ar"))
    from .activity_editorial_labels import labels as editorial_labels

    labels = dict(member_vocabulary(language)[1])
    labels.update(extra)
    labels.update(editorial_labels(language))
    return dict(
        language=language,
        labels=labels,
        category_labels=[(key, labels[key]) for key in activity_editorial.CATEGORIES],
        direction="rtl" if language == "ar" else "ltr",
        owner_testing=getattr(settings, "ANTHEEC_OWNER_TESTING", False),
    )


def go(request, name, *args):
    return redirect(reverse(name, args=args) + "?lang=" + context(request)["language"])


class TranslationFormPreview(Exception):
    pass


def translate_form(request, form, ctx, activity_id=None):
    from .activity_translation import generate, TranslationUnavailable

    mode = request.POST.get("translation_action", "")
    if mode not in {"", "preview", "direct", "publish"}:
        form.add_error(None, ctx["labels"]["error"])
        return False
    if mode not in {"preview", "direct"}:
        return True
    if not form.cleaned_data.get("translation_public"):
        form.add_error(None, ctx["labels"]["translation_public"])
        return False
    try:
        translated = generate(
            request,
            key=form.cleaned_data["key"],
            presentation=form.cleaned_data["presentation"],
            source=form.cleaned_data.get("translation_source") or "ar",
            replace=form.cleaned_data.get("translation_replace", False),
            activity_id=activity_id,
            direct=mode == "direct",
        )
    except (TranslationUnavailable, ValidationError):
        form.add_error(None, ctx["labels"]["translation_failed"])
        values = form.data.copy()
        values["key"] = str(uuid.uuid4())
        form.data = values
        return False
    form.cleaned_data["presentation"] = translated
    form.cleaned_data["event_title"] = translated["translations"]["ar"]["title"]
    values = form.data.copy()
    for lang, fields in translated["translations"].items():
        for field, value in fields.items():
            values[
                (
                    "event_title"
                    if field == "title" and lang == "ar"
                    else field + "_" + lang
                )
            ] = value
    form.data = values
    ctx["translation_generated"] = True
    return mode != "preview"


def publish_from_form(request, form, activity_id, key, reason):
    if request.POST.get("translation_action") in {"direct", "publish"}:
        activity_editorial.publish(
            request, key=key + ":publish", activity_id=activity_id, reason=reason
        )


def form_payload(data):
    data = {
        field: data[field]
        for field in (
            "key",
            "event_title",
            "starts_on",
            "ends_on",
            "capacity",
            "allows_minors",
            "consent_version",
            "consent_text",
            "reason",
            "presentation",
        )
    }
    key = str(data.pop("key"))
    data["title"] = data.pop("event_title")
    for field in ("starts_on", "ends_on"):
        data[field] = data[field].isoformat()
    return key, data


def decorate_activity(row, language):
    row.content = activity_editorial.display(row, language)
    row.ended = row.ends_on < timezone.localdate()
    return row


def image_query():
    return Prefetch(
        "editorial_images",
        queryset=ActivityImage.objects.filter(active=True).defer("jpeg").order_by("pk"),
        to_attr="public_images",
    )


@never_cache
@require_http_methods(["GET"])
@localized
def listing(request):
    ctx = context(request)
    past = request.GET.get("period") == "past"
    rows = Activity.objects.filter(is_published=True).prefetch_related(image_query())
    rows = (
        rows.filter(ends_on__lt=timezone.localdate()).order_by("-starts_on", "-pk")
        if past
        else rows.filter(ends_on__gte=timezone.localdate()).order_by("starts_on", "pk")
    )
    page = Paginator(rows, 12).get_page(request.GET.get("page"))
    for row in page:
        decorate_activity(row, ctx["language"])
    mine = []
    if request.user.is_authenticated:
        mine = list(
            Registration.objects.filter(
                Q(person__user=request.user, person__minor=False)
                | Q(person__guardian=request.user, person__minor=True)
            )
            .select_related("activity", "person")
            .order_by("-pk")[:100]
        )
        for row in mine:
            row.display_state = ctx["labels"][row.state]
    ctx.update(activities=page, page_obj=page, past=past, mine=mine)
    return render(request, "governance/activity_list.html", ctx)


@never_cache
@require_http_methods(["GET"])
@localized
def public_detail(request, activity_id):
    row = get_object_or_404(
        Activity.objects.prefetch_related(image_query()), pk=activity_id
    )
    if not row.is_published and not allows(request, "activity.view"):
        raise Http404
    ctx = context(request)
    content = activity_editorial.display(row, ctx["language"])
    ctx.update(
        row=decorate_activity(row, ctx["language"]),
        preview=not row.is_published,
        category_label=ctx["labels"][content["category"]],
        format_label=ctx["labels"][content["format"]],
    )
    return render(request, "governance/activity_public_detail.html", ctx)


@never_cache
@require_http_methods(["GET"])
def editorial_image(request, activity_id, serial):
    row = get_object_or_404(
        ActivityImage.objects.select_related("activity"),
        activity_id=activity_id,
        serial=serial,
        active=True,
    )
    if not row.activity.is_published and not allows(request, "activity.view"):
        raise Http404
    response = HttpResponse(bytes(row.jpeg), content_type="image/jpeg")
    response["Content-Disposition"] = 'inline; filename="activity.jpg"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


def upload_from_form(request, row_id, form, key, reason):
    upload = form.cleaned_data.get("image_file")
    if upload:
        raw = upload.read(activity_editorial.MAX_INPUT + 1)
        if len(raw) > activity_editorial.MAX_INPUT:
            raise ValidationError("Image too large")
        activity_editorial.upload_image(
            request,
            key=key,
            activity_id=row_id,
            image_data=base64.b64encode(raw).decode(),
            caption=form.cleaned_data.get("caption", ""),
            reason=reason,
        )


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET", "POST"])
@localized
def participate(request, activity_id):
    row = get_object_or_404(Activity, pk=activity_id, ends_on__gte=timezone.localdate())
    ctx = context(request)
    form = RegistrationForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        activity=row,
        labels=ctx["labels"],
    )
    status = 200
    if request.method == "POST":
        require_applications_enabled()
        if form.is_valid():
            data = dict(form.cleaned_data)
            person = data.pop("person")
            try:
                services.register(row, person, request.user, **data)
                return go(request, "activity_list")
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["error"])
                status = 403
            except ValidationError:
                form.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    ctx.update(row=row, form=form)
    return render(request, "governance/activity_participate.html", ctx, status=status)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def register(request):
    read_authority(request, "activity.view")
    ctx = context(request)
    form = ActivityForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        labels=ctx["labels"],
        initial={"key": uuid.uuid4()},
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                ready = translate_form(request, form, ctx)
                if not ready:
                    raise TranslationFormPreview()
                key, data = form_payload(form.cleaned_data)
                with transaction.atomic():
                    result = activity_services.create(request, key=key, **data)
                    upload_from_form(
                        request, result["activity"], form, key, data["reason"]
                    )
                    publish_from_form(
                        request, form, result["activity"], key, data["reason"]
                    )
                return go(request, "activity_admin_detail", result["activity"])
            except TranslationFormPreview:
                status = 400 if form.errors else 200
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["error"])
                status = 403
            except ValidationError:
                form.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    rows = list(Activity.objects.order_by("-pk")[:100])
    for row in rows:
        decorate_activity(row, ctx["language"])
    ctx.update(form=form, activities=rows)
    return render(request, "governance/activity_register.html", ctx, status=status)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def detail(request, activity_id):
    read_authority(request, "activity.view")
    ctx = context(request)
    row = get_object_or_404(Activity, pk=activity_id)
    initial = {
        field: getattr(row, field)
        for field in (
            "starts_on",
            "ends_on",
            "capacity",
            "allows_minors",
            "consent_version",
            "consent_text",
        )
    }
    initial.update(event_title=row.title, key=uuid.uuid4())
    form = ActivityForm(
        (
            request.POST
            if request.method == "POST" and request.POST.get("action", "edit") == "edit"
            else None
        ),
        (
            request.FILES
            if request.method == "POST" and request.POST.get("action", "edit") == "edit"
            else None
        ),
        labels=ctx["labels"],
        initial=initial,
        presentation=row.presentation,
    )
    decision = EditorialDecisionForm(
        (
            request.POST
            if request.method == "POST"
            and request.POST.get("action") in {"publish", "hide"}
            else None
        ),
        labels=ctx["labels"],
        initial={"key": uuid.uuid4()},
    )
    removal_form = EditorialDecisionForm(
        (
            request.POST
            if request.method == "POST" and request.POST.get("action") == "remove_image"
            else None
        ),
        labels=ctx["labels"],
        initial={"key": uuid.uuid4()},
    )
    image_form = ActivityImageForm(
        (
            request.POST
            if request.method == "POST" and request.POST.get("action") == "upload_image"
            else None
        ),
        (
            request.FILES
            if request.method == "POST" and request.POST.get("action") == "upload_image"
            else None
        ),
        labels=ctx["labels"],
        initial={"key": uuid.uuid4()},
    )
    status = 200
    if request.method == "POST":
        action = request.POST.get("action", "edit")
        active = (
            form
            if action == "edit"
            else (
                image_form
                if action == "upload_image"
                else removal_form if action == "remove_image" else decision
            )
        )
        if action not in {"edit", "upload_image", "publish", "hide", "remove_image"}:
            return HttpResponse(ctx["labels"]["error"], status=400)
        elif active.is_valid():
            try:
                if action == "edit" and not translate_form(request, form, ctx, row.pk):
                    raise TranslationFormPreview()
                with transaction.atomic():
                    key = str(active.cleaned_data["key"])
                    if action == "edit":
                        key, data = form_payload(form.cleaned_data)
                        activity_services.update(
                            request, key=key, activity_id=row.pk, **data
                        )
                        upload_from_form(request, row.pk, form, key, data["reason"])
                        publish_from_form(request, form, row.pk, key, data["reason"])
                    elif action == "upload_image":
                        upload_from_form(
                            request,
                            row.pk,
                            image_form,
                            key,
                            image_form.cleaned_data["reason"],
                        )
                    elif action == "remove_image":
                        activity_editorial.remove_image(
                            request,
                            key=key,
                            activity_id=row.pk,
                            image_serial=request.POST.get("image_serial", ""),
                            reason=removal_form.cleaned_data["reason"],
                        )
                    else:
                        getattr(activity_editorial, action)(
                            request,
                            key=key,
                            activity_id=row.pk,
                            reason=decision.cleaned_data["reason"],
                        )
                return go(request, "activity_admin_detail", row.pk)
            except TranslationFormPreview:
                status = 400 if form.errors else 200
            except PermissionDenied:
                active.add_error(None, ctx["labels"]["error"])
                status = 403
            except (ValidationError, ValueError, ObjectDoesNotExist):
                active.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    from .capabilities import allows

    rows = list(
        Registration.objects.filter(activity=row)
        .select_related("person")
        .order_by("-pk")[:100]
    )
    if not allows(request, "registration.view"):
        rows = []
    attended = (
        set(
            Attendance.objects.filter(registration__activity=row).values_list(
                "registration_id", flat=True
            )
        )
        if allows(request, "attendance.view")
        else set()
    )
    for item in rows:
        item.display_state = ctx["labels"][item.state]
        item.display_attendance = (
            ctx["labels"]["present" if item.pk in attended else "absent"]
            if allows(request, "attendance.view")
            else "—"
        )
    ctx.update(
        row=decorate_activity(row, ctx["language"]),
        form=form,
        registrations=rows,
        decision=decision,
        removal_form=removal_form,
        image_form=image_form,
        images=row.editorial_images.filter(active=True).defer("jpeg").order_by("pk"),
        can_edit=allows(request, "activity.edit")
        and (not row.is_published or allows(request, "activity.publish")),
        can_upload=allows(request, "activity.image_upload")
        and (not row.is_published or allows(request, "activity.publish")),
    )
    return render(request, "governance/activity_detail.html", ctx, status=status)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def admission(request, registration_id):
    read_authority(request, "registration.view")
    ctx = context(request)
    row = get_object_or_404(
        Registration.objects.select_related("activity", "person", "submitted_by"),
        pk=registration_id,
    )
    form = DecisionForm(
        (
            request.POST
            if request.method == "POST" and request.POST.get("operation") != "checkin"
            else None
        ),
        labels=ctx["labels"],
        initial={"key": uuid.uuid4()},
    )
    if request.method == "GET":
        choices = (
            ["cancel"]
            if row.state == "confirmed"
            else (
                ["reject", "cancel"]
                if ctx["owner_testing"]
                else ["accept", "reject", "cancel"]
            )
        )
        form.fields["operation"].choices = [
            (value, ctx["labels"][value]) for value in choices
        ]
    checkin = CheckinForm(
        (
            request.POST
            if request.method == "POST" and request.POST.get("operation") == "checkin"
            else None
        ),
        initial={"key": uuid.uuid4()},
    )
    doc = (
        Document.objects.filter(registration=row, kind="invitation", void=False)
        .order_by("-pk")
        .first()
    )
    status = 200
    active = checkin if request.POST.get("operation") == "checkin" else form
    if request.method == "POST":
        if active.is_valid():
            data = active.cleaned_data
            key = str(data["key"])
            try:
                operation = request.POST.get("operation")
                if operation == "checkin":
                    if not doc:
                        raise ValidationError("Invitation required")
                    services.check_in(request, key=key, document_id=doc.pk)
                elif operation == "cancel":
                    services.cancel_registration(
                        request, key=key, registration_id=row.pk, reason=data["reason"]
                    )
                else:
                    if operation == "accept":
                        require_issuance_enabled()
                    services.decide_registration(
                        request,
                        key=key,
                        registration_id=row.pk,
                        accept=operation == "accept",
                        reason=data["reason"],
                    )
                return go(request, "activity_admission", row.pk)
            except PermissionDenied:
                active.add_error(None, ctx["labels"]["error"])
                status = 403
            except ValidationError:
                active.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    restrict_choices(
        request,
        form,
        "operation",
        {
            "accept": "registration.approve",
            "reject": "registration.reject",
            "cancel": "registration.cancel",
        },
    )
    ctx.update(
        row=row,
        form=form,
        checkin=checkin,
        can_checkin=bool(doc and services.document_status(doc) == "active"),
        display_state=ctx["labels"][row.state],
        display_attendance=(
            ctx["labels"][
                (
                    "present"
                    if Attendance.objects.filter(registration=row).exists()
                    else "absent"
                )
            ]
            if allows(request, "attendance.view")
            else "—"
        ),
        history=Audit.objects.filter(
            subject=str(row.pk),
            action__in=["registration.decided", "registration.cancelled"],
        ).order_by("pk"),
    )
    return render(request, "governance/activity_admission.html", ctx, status=status)
