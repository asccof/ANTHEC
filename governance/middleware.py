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
            primary = bool(authority and authority.primary_id == request.user.pk)
            if primary:
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
                    (primary and not request.user.is_verified())
                    or request.session.get("authority_epoch") != epoch
                ):
                    if not primary:
                        return HttpResponseForbidden("Delegation changed; sign out and sign in again")
                    target = reverse("security_challenge")
                    if "lang" in request.GET:
                        target += "?lang=" + vocabulary(request.GET["lang"])[0]
                    return redirect(target)
        if request.path.startswith('/admin/') and request.user.is_authenticated and not Authority.objects.filter(pk=1, primary=request.user).exists():
            from django.db import transaction
            from .services import authorize
            # Hold the same authority lock through native CMS writes, so a
            # concurrent revoke cannot slip between the check and persistence.
            with transaction.atomic():
                authorize(request, capability=(), recent=False)
                response = self.get_response(request)
                if response.status_code >= 400:
                    transaction.set_rollback(True)
                return response
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith("/admin/") and request.user.is_authenticated:
            if not Authority.objects.filter(pk=1, primary=request.user).exists():
                from .delegation_cms import check_admin_route
                from .capabilities import enforce
                if request.path == "/admin/":
                    enforce(request)
                    return redirect("delegated_workspace")
                response = check_admin_route(request, request.resolver_match)
                if response is not None: return response
                if (request.resolver_match.view_name == 'wagtailsettings:edit'
                    and request.resolver_match.kwargs.get('app_name') == 'content'
                    and request.resolver_match.kwargs.get('model_name') == 'publiccontact'
                    and request.method in {'GET', 'HEAD'}):
                    from .capabilities import allows
                    if not allows(request, 'contact.edit'):
                        return redirect('delegated_contact')
        return None


from django.middleware.locale import LocaleMiddleware


class PolicyLocaleMiddleware(LocaleMiddleware):
    """Keep resolved API errors stable instead of redirecting into Wagtail pages."""

    def process_response(self, request, response):
        from django.conf import settings
        if ((getattr(settings, "ANTHEEC_OWNER_TESTING", False) or getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False))
                and getattr(response, "anthec_private_denial", False)):
            # The private gate runs before URL resolution. Do not convert its
            # denials into locale-prefixed Wagtail catch-all redirects.
            return response
        match = getattr(request, "resolver_match", None)
        if match and match.func.__module__.startswith("governance."):
            return response
        result = super().process_response(request, response)
        if (getattr(settings, "ANTHEEC_OWNER_TESTING", False) or getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False)
                or getattr(settings, "ANTHEEC_OPERATIONAL", False)):
            # LocaleMiddleware can replace the response with a redirect. Keep
            # the private cache/indexing headers on that replacement as well.
            result["Cache-Control"] = "no-store, private"
            if result is not response or "X-Robots-Tag" not in result:
                result["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return result
