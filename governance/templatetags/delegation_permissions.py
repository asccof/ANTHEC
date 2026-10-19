from django import template
from governance.capabilities import allows

register = template.Library()
register.filter("cap", allows)


@register.filter
def has_admin_workspace(request):
    from governance.capabilities import ALL_CAPABILITIES

    # Use the same active-grant/session boundary as the displayed sections.
    return any(allows(request, capability) for capability in ALL_CAPABILITIES)
