from django import template
from governance.capabilities import allows

register = template.Library()
register.filter("cap", allows)


@register.filter
def has_admin_workspace(request):
    from governance.models import Authority, Delegation
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_active and (
        Authority.objects.filter(pk=1, primary=user).exists()
        or Delegation.objects.filter(user=user, active=True).exists()
    ))
