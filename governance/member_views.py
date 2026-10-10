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
        "language": language,
        "labels": labels,
        "direction": "rtl" if language == "ar" else "ltr",
    }


def go(request, name):
    from django.urls import reverse

    return redirect(reverse(name) + "?lang=" + context(request)["language"])


def auth_attempt(request):
    # One hashed IP bucket covers signup/signin. Fixed window, no identities logged.
    key = services.digest(
        f'member-auth:{request.META.get("REMOTE_ADDR", "")}:{int(timezone.now().timestamp() // 300)}'
    )
    with transaction.atomic():
        row, _ = RateBucket.objects.get_or_create(key=key)
        row = RateBucket.objects.select_for_update().get(pk=key)
        row.count += 1
        row.save(update_fields=["count"])
        return row.count <= 10


@never_cache
@sensitive_post_parameters("password", "password1", "password2")
@require_http_methods(["GET", "POST"])
@localized
def account(request, mode):
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
                        user = form.save()
                        services.audit(user, "member.account.created", user.pk)
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
                    services.authorize(request)
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
        # A password change must not retain sensitive-operation reauthentication.
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
    ctx.update(
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
        {k: getattr(person, k) for k in ("full_name", "contact", "directory_consent")}
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
    if not Person.objects.filter(user=request.user).exists():
        return go(request, "member_profile")
    form = ApplicationForm(
        request.POST if request.method == "POST" else None, labels=ctx["labels"]
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                member_services.submit_application(
                    request.user,
                    tier=form.cleaned_data["tier"],
                    key=str(form.cleaned_data["key"]),
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
