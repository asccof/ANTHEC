from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from .member_labels import vocabulary
from .models import Authority, Delegation


class AdminSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith(("/admin/", "/operations/", "/security/"))
            and request.user.is_authenticated
        ):
            authority = Authority.objects.filter(pk=1).first()
            if authority and authority.primary_id == request.user.pk:
                epoch = 0
            else:
                delegation = Delegation.objects.filter(
                    user=request.user, active=True
                ).first()
                if not delegation:
                    return HttpResponseForbidden("Administrative authority required")
                epoch = delegation.epoch
                # Even explicit unrelated Django permissions must not allow a
                # delegate to change users/groups, devices or the primary director.
                if request.path.startswith(("/admin/users/", "/admin/groups/")):
                    return HttpResponseForbidden("Primary director only")
            if not request.path.startswith("/security/"):
                if (
                    not request.user.is_verified()
                    or request.session.get("authority_epoch") != epoch
                ):
                    target = reverse("security_challenge")
                    if "lang" in request.GET:
                        target += "?lang=" + vocabulary(request.GET["lang"])[0]
                    return redirect(target)
        return self.get_response(request)


from django.middleware.locale import LocaleMiddleware


class PolicyLocaleMiddleware(LocaleMiddleware):
    """Keep resolved API errors stable instead of redirecting into Wagtail pages."""

    def process_response(self, request, response):
        from django.conf import settings
        if (getattr(settings, "ANTHEEC_OWNER_TESTING", False)
                and response.status_code == 404 and response.get("X-Robots-Tag")):
            # The private gate runs before URL resolution. Do not convert its
            # denials into locale-prefixed Wagtail catch-all redirects.
            return response
        match = getattr(request, "resolver_match", None)
        if match and match.func.__module__.startswith("governance."):
            return response
        return super().process_response(request, response)
