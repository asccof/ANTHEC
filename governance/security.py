"""Password + TOTP with hashed one-use recovery codes and per-account throttling."""

import secrets
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django_otp import login as otp_login, verify_token
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import Authority, Delegation, RecoveryCode, RateBucket
from .services import digest, audit
from .member_views import context as member_context, localized as member_localized


def epoch_for(user):
    if Authority.objects.filter(pk=1, primary=user).exists():
        return 0
    row = Delegation.objects.filter(user=user, active=True).first()
    if not row or not user.is_active:
        raise PermissionDenied("Administrative authority revoked")
    return row.epoch


def consume_attempt(user):
    window = int(timezone.now().timestamp() // 300)
    with transaction.atomic():
        row, _ = RateBucket.objects.get_or_create(
            key=digest(f"auth:{user.pk}:{window}")
        )
        row = RateBucket.objects.select_for_update().get(pk=row.pk)
        row.count += 1
        row.save(update_fields=["count"])
        return row.count <= 10


def authenticate_factor(user, code, recovery=False):
    if recovery:
        with transaction.atomic():
            row = (
                RecoveryCode.objects.select_for_update()
                .filter(user=user, digest=digest(code), used_at=None)
                .first()
            )
            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            if not row or not device:
                return None
            row.used_at = timezone.now()
            row.save(update_fields=["used_at"])
            audit(user, "security.recovery.used", user.pk)
            return device
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    return verify_token(user, device.persistent_id, code) if device else None


@never_cache
@sensitive_post_parameters("password", "code")
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@member_localized
def challenge(request):
    if not Authority.objects.filter(pk=1, primary=request.user).exists():
        from .capabilities import enforce
        enforce(request)
        return redirect("delegated_workspace")
    if request.user.is_verified() and request.session.get("authority_epoch") == 0:
        return redirect("/admin/")
    ctx = member_context(request)
    error = ""
    if request.method == "POST":
        if not consume_attempt(request.user) or not request.user.check_password(
            request.POST.get("password", "")
        ):
            error = ctx["labels"]["error"]
        else:
            device = authenticate_factor(
                request.user,
                request.POST.get("code", ""),
                request.POST.get("recovery") == "on",
            )
            if device:
                request.session.cycle_key()
                otp_login(request, device)
                request.session["authority_epoch"] = epoch_for(request.user)
                request.session["reauth_at"] = timezone.now().timestamp()
                audit(request.user, "security.mfa.verified", request.user.pk)
                return redirect("/admin/")
            error = ctx["labels"]["error"]
        audit(request.user, "security.mfa.failed", request.user.pk)
    return render(
        request,
        "governance/challenge.html",
        {
            **ctx,
            "error": error,
            "enrolled": TOTPDevice.objects.filter(
                user=request.user, confirmed=True
            ).exists(),
        },
    )


@never_cache
@sensitive_post_parameters("password", "code")
@login_required(login_url="/admin/login/")
@require_http_methods(["GET", "POST"])
@member_localized
def enroll(request):
    if not Authority.objects.filter(pk=1, primary=request.user).exists():
        raise PermissionDenied("Only the primary director enrolls administrative MFA")
    if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return HttpResponseForbidden(
            member_context(request)["labels"]["already_enrolled"]
        )
    context = member_context(request)
    if request.method == "POST":
        if not consume_attempt(request.user) or not request.user.check_password(
            request.POST.get("password", "")
        ):
            context["error"] = context["labels"]["error"]
        else:
            with transaction.atomic():
                Authority.objects.select_for_update().get(pk=1)
                if TOTPDevice.objects.filter(
                    user=request.user, confirmed=True
                ).exists():
                    return HttpResponseForbidden(context["labels"]["already_enrolled"])
                device = TOTPDevice.objects.filter(
                    user=request.user, confirmed=False
                ).first()
                if device is None:
                    device = TOTPDevice.objects.create(
                        user=request.user, confirmed=False, name="ANTHEEC"
                    )
                code = request.POST.get("code", "")
                if code and device.verify_token(code):
                    device.confirmed = True
                    device.save(update_fields=["confirmed"])
                    codes = [secrets.token_urlsafe(24) for _ in range(8)]
                    for token in codes:
                        RecoveryCode.objects.create(
                            user=request.user, digest=digest(token)
                        )
                    request.session.cycle_key()
                    otp_login(request, device)
                    request.session["authority_epoch"] = epoch_for(request.user)
                    request.session["reauth_at"] = timezone.now().timestamp()
                    audit(request.user, "security.mfa.enrolled", request.user.pk)
                    return render(
                        request, "governance/recovery.html", {**context, "codes": codes}
                    )
                context["uri"] = device.config_url
                if code:
                    context["error"] = context["labels"]["error"]
    return render(request, "governance/enroll.html", context)
