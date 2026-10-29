"""Bind account and administrative epochs at a successful login boundary."""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Authority, Delegation, MemberAccountControl


@receiver(user_logged_in, dispatch_uid="anthec_administrative_login")
def bind_administrative_login(sender, request, user, **kwargs):
    if request is None:
        return
    control = MemberAccountControl.objects.filter(user=user).first()
    if control and control.state != 'active':
        from django.contrib.auth import logout
        from django.core.exceptions import PermissionDenied
        logout(request)
        raise PermissionDenied('Inactive account')
    request.session['member_account_epoch'] = control.epoch if control else 0
    for key in ("authority_epoch", "reauth_at", "otp_device_id"):
        request.session.pop(key, None)
    user.otp_device = None
    if Authority.objects.filter(pk=1, primary=user).exists():
        return  # Only the primary's successful second factor binds epoch zero.
    row = Delegation.objects.filter(user=user, active=True).first()
    if row and user.is_active:
        from .capabilities import validate_capabilities
        from django.core.exceptions import ValidationError
        try:
            validate_capabilities(row.capabilities)
        except ValidationError:
            return
        request.session["authority_epoch"] = row.epoch
