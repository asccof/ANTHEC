from functools import wraps
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.db import transaction, IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import translation, timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST
from . import member_services, services
from .member_forms import (
    SignupForm,
    LoginForm,
    ChangePasswordForm,
    ProfileForm,
    ApplicationForm,
)
from .member_labels import vocabulary
from .models import Person, Application, RateBucket


def localized(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        language, labels = vocabulary(request.GET.get("lang", "ar"))
        with translation.override(language):
            return view(request, *args, **kwargs)

    return wrapped


def context(request):
    language, labels = vocabulary(request.GET.get("lang", "ar"))
    return {
        "submit_label": labels.get(
            {
                "/members/signup/": "signup",
                "/members/login/": "login",
                "/members/profile/": "save_profile",
                "/members/apply/": "submit_application",
                "/members/renew/": "renew",
                "/members/password/": "change_password",
            }.get(request.path, "save")
        ),
        "language": language,
        "labels": labels,
        "direction": "rtl" if language == "ar" else "ltr",
    }


def go(request, name):
    from django.urls import reverse

    return redirect(reverse(name) + "?lang=" + context(request)["language"])


def auth_attempt(request):
    from .public_limits import consume
    identity = request.POST.get("username") or (request.user.get_username() if request.user.is_authenticated else "")
    return consume(request, "auth", identity=identity)



@never_cache
@sensitive_post_parameters("password", "password1", "password2")
@require_http_methods(["GET", "POST"])
@localized
def account(request, mode):
    if mode == "signup":
        from .deployment import require_applications_enabled
        require_applications_enabled()
    if request.user.is_authenticated:
        return go(request, "member_home")
    ctx = context(request)
    status = 200
    data = request.POST if request.method == "POST" else None
    form = (
        SignupForm(data, labels=ctx["labels"])
        if mode == "signup"
        else LoginForm(request, data=data, labels=ctx["labels"])
    )
    if request.method == "POST":
        if not auth_attempt(request):
            ctx["error"] = ctx["labels"]["limited"]
            status = 429
        elif form.is_valid():
            if mode == "signup":
                try:
                    with transaction.atomic():
                        from .privacy_notice import pop_ack, record
                        evidence = pop_ack(dict(form.cleaned_data))
                        user = form.save()
                        services.audit(user, "member.account.created", user.pk)
                        record(user, 'member.signup', user.pk, evidence)
                except IntegrityError:
                    form.add_error(None, ctx["labels"]["error"])
                    return render(
                        request,
                        "governance/member_form.html",
                        {**ctx, "form": form, "title": ctx["labels"][mode]},
                        status=400,
                    )
            else:
                user = form.get_user()
                services.audit(user, "member.account.login", user.pk)
            login(request, user)
            from .models import Authority, Delegation
            if Authority.objects.filter(pk=1, primary=user).exists():
                return go(request, "security_challenge")
            if Delegation.objects.filter(user=user, active=True).exists():
                return go(request, "delegated_workspace")
            # Public activity participation resumes after ordinary member login.
            from django.utils.http import url_has_allowed_host_and_scheme
            target = request.GET.get("next", "")
            if target.startswith("/activities/") and url_has_allowed_host_and_scheme(
                target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(target)
            return go(request, "member_home")
        else:
            services.audit(
                None, "member.account.failed", "signin" if mode == "login" else "signup"
            )
            status = 400
    return render(
        request,
        "governance/member_form.html",
        {**ctx, "form": form, "title": ctx["labels"][mode]},
        status=status,
    )


@never_cache
@login_required(login_url="/members/login/")
@require_POST
def signout(request):
    services.audit(request.user, "member.account.logout", request.user.pk)
    logout(request)
    return go(request, "member_login")


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET", "POST"])
@localized
@sensitive_post_parameters("old_password", "new_password1", "new_password2")
def password(request):
    ctx = context(request)
    form = ChangePasswordForm(
        request.user,
        request.POST if request.method == "POST" else None,
        labels=ctx["labels"],
    )
    if request.method == "POST" and not auth_attempt(request):
        return render(
            request,
            "governance/member_form.html",
            {
                **ctx,
                "form": form,
                "title": ctx["labels"]["change_password"],
                "error": ctx["labels"]["limited"],
            },
            status=429,
        )
    if request.method == "POST" and form.is_valid():
        from .models import Authority, Delegation

        try:
            with transaction.atomic():
                authority = Authority.objects.select_for_update().filter(pk=1).first()
                user = (
                    get_user_model().objects.select_for_update().get(pk=request.user.pk)
                )
                if not user.is_active or not user.check_password(
                    request.POST.get("old_password", "")
                ):
                    raise PermissionDenied("Current credentials required")
                if (
                    authority and authority.primary_id == user.pk
                ) or Delegation.objects.filter(user=user, active=True).exists():
                    services.authorize(request, capability=())
                form.user = user
                user = form.save()
                services.audit(user, "member.password.changed", user.pk)
        except PermissionDenied:
            services.audit(request.user, "member.password.denied", request.user.pk)
            form.add_error(None, ctx["labels"]["reauth"])
            return render(
                request,
                "governance/member_form.html",
                {**ctx, "form": form, "title": ctx["labels"]["change_password"]},
                status=403,
            )
        update_session_auth_hash(request, user)
        # Discard the obsolete operation-reauthentication timestamp.
        request.session.pop("reauth_at", None)
        return go(request, "member_home")
    return render(
        request,
        "governance/member_form.html",
        {**ctx, "form": form, "title": ctx["labels"]["change_password"]},
        status=400 if request.method == "POST" else 200,
    )


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET"])
@localized
def home(request):
    ctx = context(request)
    person = Person.objects.filter(user=request.user).first()
    apps = Application.objects.filter(person=person).order_by("-pk") if person else []
    from .models import Membership
    from .member_forms import RenewalForm

    apps = list(apps)
    terms = Membership.objects.filter(application__person=person).select_related("application").order_by("-starts_on", "-pk") if person else []
    policy_day = services.today()
    term_rows = []
    for term in terms:
        state = term.state
        if state == "active":
            if term.ends_on and policy_day >= term.ends_on:
                state = "expired"
            elif policy_day < term.starts_on:
                state = "upcoming_term"
        term_rows.append(dict(term=term, tier=ctx["labels"].get(term.application.tier, term.application.tier), state=ctx["labels"].get(state, state), state_key=state))
    ctx.update(
        membership_terms=term_rows,
        pending_count=sum(a.state == "submitted" for a in apps),
        document_count=owned_documents(request.user).count(),
        can_renew=RenewalForm(labels=ctx["labels"], user=request.user).fields["membership_id"].queryset.exists(),
        can_apply=bool(person and not term_rows and not any(a.state == "submitted" for a in apps)),
        person=person,
        applications=[
            {
                "app": a,
                "tier": ctx["labels"][a.tier],
                "state": ctx["labels"].get(a.state, a.state),
            }
            for a in apps
        ],
    )
    return render(request, "governance/member_home.html", ctx)


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET", "POST"])
@localized
def profile(request):
    ctx = context(request)
    person = Person.objects.filter(user=request.user).first()
    initial = (
        {
            k: getattr(person, k)
            for k in (
                "full_name",
                "contact",
                "phone",
                "profession",
                "directory_consent",
            )
        }
        if person
        else {}
    )
    initial["notice"] = bool(person and person.verification_notice_at)
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        labels=ctx["labels"],
        initial=initial,
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                member_services.update_profile(
                    request.user,
                    **{**form.cleaned_data, "key": str(form.cleaned_data["key"])},
                )
                return go(request, "member_home")
            except (ValidationError, ObjectDoesNotExist, PermissionDenied):
                form.add_error(None, ctx["labels"]["error"])
        status = 400
    return render(
        request,
        "governance/member_form.html",
        {**ctx, "form": form, "title": ctx["labels"]["profile"]},
        status=status,
    )


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET", "POST"])
@localized
def apply(request):
    ctx = context(request)
    person = Person.objects.filter(user=request.user).first()
    if not person or not person.phone or not person.profession:
        return go(request, "member_profile")
    form = ApplicationForm(
        request.POST if request.method == "POST" else None,
        request.FILES or None,
        labels=ctx["labels"],
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                import base64
                from .portraits import normalize

                member_services.submit_application(
                    request.user,
                    image_data=base64.b64encode(
                        normalize(form.cleaned_data["photo"])
                    ).decode(),
                    photo_consent=form.cleaned_data["photo_consent"],
                    **{
                        k: form.cleaned_data[k]
                        for k in (
                            "address_category",
                            "correspondence_address",
                            "professional_address",
                            "residential_address",
                            "same_address",
                        )
                    },
                    tier=form.cleaned_data["tier"],
                    applicant_capacity=form.cleaned_data["applicant_capacity"],
                    capacity_other=form.cleaned_data["capacity_other"],
                    key=str(form.cleaned_data["key"]),
                    **{k:v for k,v in form.cleaned_data.items() if k.startswith('privacy_')},
                )
                return go(request, "member_home")
            except (ValidationError, ObjectDoesNotExist, PermissionDenied):
                form.add_error(None, ctx["labels"]["error"])
        status = 400
    return render(
        request,
        "governance/member_form.html",
        {**ctx, "form": form, "title": ctx["labels"]["apply"]},
        status=status,
    )


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET", "POST"])
@localized
def renew(request):
    from .member_forms import RenewalForm

    ctx = context(request)
    form = RenewalForm(
        request.POST if request.method == "POST" else None,
        labels=ctx["labels"],
        user=request.user,
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                member_services.submit_renewal(
                    request.user,
                    membership_id=form.cleaned_data["membership_id"].pk,
                    key=str(form.cleaned_data["key"]),
                    **{k:v for k,v in form.cleaned_data.items() if k.startswith('privacy_')},
                )
                return go(request, "member_home")
            except (ValidationError, ObjectDoesNotExist, PermissionDenied):
                form.add_error(None, ctx["labels"]["error"])
        status = 400
    return render(
        request,
        "governance/member_form.html",
        {**ctx, "form": form, "title": ctx["labels"]["renew"]},
        status=status,
    )


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET"])
@localized
def application_detail(request, application_id):
    from django.db.models import Q
    from .models import Document, Refund, Membership

    ctx = context(request)
    app = get_object_or_404(
        Application.objects.filter(
            Q(person__user=request.user)
            | Q(person__minor=True, person__guardian=request.user)
        ),
        pk=application_id,
    )
    term = Membership.objects.filter(application=app).first()
    documents = (
        Document.objects.filter(Q(membership=term) | Q(accreditation__membership=term))
        if term
        else Document.objects.none()
    )
    ctx.update(
        declared_capacity=ctx["labels"].get(
            (
                "capacity_option_other"
                if app.applicant_capacity == "other"
                else "capacity_" + app.applicant_capacity
            ),
            "—",
        ),
        app=app,
        tier=ctx["labels"][app.tier],
        state=ctx["labels"].get(app.state, app.state),
        term=term,
        payments=[
            {
                "receipt": p.receipt,
                "amount": p.amount,
                "method": ctx["labels"][p.method],
            }
            for p in app.payment_set.order_by("pk")
        ],
        refunds=[
            {
                "receipt": r.payment.receipt,
                "amount": r.amount,
                "decision": ctx["labels"]["approve" if r.approved else "reject"],
            }
            for r in Refund.objects.filter(payment__application=app)
            .select_related("payment")
            .order_by("pk")
        ],
        documents=document_rows(ctx["labels"], documents),
    )
    return render(request, "governance/member_application.html", ctx)


def document_rows(labels, documents):
    return [
        {
            "doc": d,
            "label": labels.get(d.kind, d.kind),
            "status": labels.get(
                services.document_status(d), services.document_status(d)
            ),
        }
        for d in documents
    ]


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET"])
@localized
def documents(request):
    ctx = context(request)
    ctx["documents"] = document_rows(ctx["labels"], owned_documents(request.user).order_by("-pk"))
    return render(request, "governance/member_documents.html", ctx)


def owned_documents(user):
    """Same ownership boundary for dashboard totals and the document list."""
    from django.db.models import Q
    from .models import Document

    people = Person.objects.filter(Q(user=user) | Q(minor=True, guardian=user))
    return Document.objects.filter(
        Q(membership__application__person__in=people)
        | Q(accreditation__membership__application__person__in=people)
        | Q(institutional_role__person__in=people)
    )
