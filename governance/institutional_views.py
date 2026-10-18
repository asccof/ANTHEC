import uuid
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import translation
from functools import wraps
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import services, institutional
from .models import InstitutionalRole, Audit
from .institutional_forms import GrantForm, DecisionForm, ReplacementForm
from .institutional_labels import vocabulary


def localized(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        language, _ = vocabulary(request.GET.get("lang", "ar"))
        with translation.override(language):
            return view(request, *args, **kwargs)

    return wrapper


def context(request):
    language, labels = vocabulary(request.GET.get("lang", "ar"))
    return {
        "language": language,
        "labels": labels,
        "direction": "rtl" if language == "ar" else "ltr",
    }


def read_authority(request):
    with transaction.atomic():
        services.authorize(request, recent=False)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def register(request):
    read_authority(request)
    ctx = context(request)
    form = GrantForm(
        request.POST or None, labels=ctx["labels"], initial={"key": uuid.uuid4()}
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            try:
                result = institutional.grant(
                    request,
                    key=str(data["key"]),
                    person_id=data["person_id"].pk,
                    role=data["role"],
                    starts_on=data["starts_on"].isoformat(),
                    ends_on=data["ends_on"].isoformat() if data["ends_on"] else None,
                    legal_reference=data["legal_reference"],
                    reason=data["reason"],
                    replaces_role_id=(
                        data["replaces_role_id"].pk
                        if data["replaces_role_id"]
                        else None
                    ),
                )
                return redirect(
                    reverse("institutional_detail", args=[result["institutional_role"]])
                    + "?lang="
                    + ctx["language"]
                )
            except PermissionDenied:
                form.add_error(None, ctx["labels"]["reauth"])
                status = 403
            except (ValidationError, ObjectDoesNotExist):
                form.add_error(None, ctx["labels"]["error"])
                status = 400
        else:
            status = 400
    ctx.update(
        form=form,
        rows=[
            {
                "role": row,
                "label": ctx["labels"][row.role],
                "state_label": ctx["labels"][row.state],
            }
            for row in InstitutionalRole.objects.select_related("person").order_by(
                "-pk"
            )[:100]
        ],
    )
    return render(request, "governance/institutional_register.html", ctx, status=status)


@never_cache
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@localized
def detail(request, role_id):
    read_authority(request)
    row = get_object_or_404(
        InstitutionalRole.objects.select_related("person"), pk=role_id
    )
    ctx = context(request)
    documents = row.document_set.order_by("version")
    decision = DecisionForm(
        labels=ctx["labels"],
        founder=row.role in {"founder", "honorary"},
        initial={"key": uuid.uuid4(), "state": row.state},
    )
    replacement = ReplacementForm(
        labels=ctx["labels"], documents=documents, initial={"key": uuid.uuid4()}
    )
    status = 200
    if request.method == "POST":
        action = request.POST.get("action")
        form = (
            decision
            if action == "state"
            else replacement if action == "replace" else None
        )
        if form is None:
            status = 400
        else:
            form = form.__class__(
                request.POST,
                labels=ctx["labels"],
                **(
                    {"founder": row.role in {"founder", "honorary"}}
                    if action == "state"
                    else {"documents": documents}
                )
            )
            if action == "state":
                decision = form
            else:
                replacement = form
            if form.is_valid():
                data = form.cleaned_data
                try:
                    if action == "state":
                        institutional.change_state(
                            request,
                            key=str(data["key"]),
                            role_id=row.pk,
                            state=data["state"],
                            reason=data["reason"],
                        )
                    else:
                        services.replace_document(
                            request,
                            key=str(data["key"]),
                            document_id=data["document_id"].pk,
                            reason=data["reason"],
                        )
                    return redirect(
                        reverse("institutional_detail", args=[row.pk])
                        + "?lang="
                        + ctx["language"]
                    )
                except PermissionDenied:
                    form.add_error(None, ctx["labels"]["reauth"])
                    status = 403
                except (ValidationError, ObjectDoesNotExist):
                    form.add_error(None, ctx["labels"]["error"])
                    status = 400
            else:
                status = 400
    ctx.update(
        row=row,
        role_label=ctx["labels"][row.role],
        state_label=ctx["labels"][row.state],
        decision=decision,
        replacement=replacement,
        documents=[
            {"document": doc, "status": ctx["labels"][services.document_status(doc)]}
            for doc in documents
        ],
        history=Audit.objects.filter(
            Q(action__startswith="institutional.", subject=str(row.pk))
            | Q(
                action="document.replaced",
                subject__in=[str(doc.pk) for doc in documents],
            )
        ).order_by("pk"),
    )
    return render(request, "governance/institutional_detail.html", ctx, status=status)
