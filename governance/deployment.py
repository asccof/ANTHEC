"""Temporary deployment restrictions, separate from approved domain policies."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.storage import Storage
from django.db import transaction
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.utils import timezone
from .models import Authority, RateBucket


def workflow_disabled(name):
    return bool(
        getattr(settings, "ANTHEEC_OWNER_TESTING", False)
        or getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False)
        or not getattr(settings, f"ANTHEEC_{name}_ENABLED", True)
    )


def presentation_context(request):
    from .privacy_notice import enabled
    return {
        'privacy_notice_enabled': enabled(),
        "public_preview": getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False),
        "operational": getattr(settings, "ANTHEEC_OPERATIONAL", False),
        "applications_disabled": workflow_disabled("APPLICATIONS"),
        "verification_disabled": bool(
            getattr(settings, "ANTHEEC_OWNER_TESTING", False)
            or getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False)
        ),
    }


def require_issuance_enabled():
    if workflow_disabled("ISSUANCE"):
        raise PermissionDenied("Document issuance and generation are disabled in this deployment.")


def require_applications_enabled():
    if workflow_disabled("APPLICATIONS"):
        raise PermissionDenied("Applications and registrations are disabled in this deployment.")


def require_payments_enabled():
    if workflow_disabled("PAYMENTS"):
        raise PermissionDenied("Payments and refunds are disabled in this deployment.")


class DisabledMediaStorage(Storage):
    def _open(self, name, mode="rb"):
        raise PermissionDenied("Filesystem media is unavailable during owner testing.")

    def _save(self, name, content):
        raise PermissionDenied("Filesystem uploads are disabled in this deployment.")

    def exists(self, name):
        return False

    def url(self, name):
        raise PermissionDenied("Private media has no public URL.")


class OwnerTestingMiddleware:
    """Only the active MFA-verified primary sees dynamic application data."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "ANTHEEC_OWNER_TESTING", False):
            return self.get_response(request)
        response = self.restricted_response(request)
        response["Cache-Control"] = "no-store, private"
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response

    @staticmethod
    def denied(message):
        response = HttpResponseNotFound(message)
        response.anthec_private_denial = True
        return response

    def restricted_response(self, request):
        path = request.path_info
        if path == "/health/" and request.method in {"GET", "HEAD"}:
            return self.get_response(request)
        if path == "/admin/login/":
            return self.get_response(request)
        if path == "/admin/logout/":
            return self.get_response(request)
        user = request.user
        if not (user.is_authenticated and user.is_active and
                Authority.objects.filter(pk=1, primary_id=user.pk).exists()):
            return self.denied("Private owner testing")
        if path in {"/security/enroll/", "/security/challenge/"}:
            return self.get_response(request)
        if not user.is_verified() or request.session.get("authority_epoch") != 0:
            return redirect("/security/challenge/")
        if path.startswith(("/members/signup/", "/members/apply/", "/members/renew/",
                            "/registrations/", "/verify/", "/my-documents/")):
            return self.denied("Unavailable during owner testing")
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # CsrfViewMiddleware precedes this hook. Rejected CSRF requests never
        # consume the budget. Render's REMOTE_ADDR is a shared ingress peer,
        # not a client identity; use only the explicit global ceiling and do
        # not trust client-supplied forwarding headers.
        if (not (getattr(settings, "ANTHEEC_OWNER_TESTING", False) or
                     getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False)) or
                request.path_info != "/admin/login/" or request.method != "POST"):
            return None
        return self.login_budget()

    @staticmethod
    def login_budget():
        from .public_limits import prune_expired
        prune_expired()
        from .services import digest
        window = int(timezone.now().timestamp() // 300)
        key = digest(f"private-login-global:{window}")
        with transaction.atomic():
            bucket, _ = RateBucket.objects.get_or_create(key=key)
            bucket = RateBucket.objects.select_for_update().get(pk=bucket.pk)
            bucket.count += 1
            bucket.save(update_fields=["count"])
        if bucket.count > 50:
            return HttpResponse("Try again later", status=429)
        return None


class PublicPreviewMiddleware(OwnerTestingMiddleware):
    """Allow only public editorial GET/HEAD routes; retain primary-only administration.

    This is not a real-data production mode. Unknown/new endpoints are denied
    until deliberately included, even if their view has no authentication check.
    """
    PUBLIC_VIEWS = {
        "partners", "activity_list", "activity_public_detail", "activity_editorial_image"
    }

    def public_read(self, request):
        if request.method not in {"GET", "HEAD"}:
            return False
        if request.path_info == "/":
            return True  # LocaleMiddleware selects the public homepage.
        try:
            match = resolve(request.path_info, urlconf=getattr(request, "urlconf", None))
        except Resolver404:
            return False
        from wagtail.views import serve
        return match.view_name in self.PUBLIC_VIEWS or match.func is serve

    def __call__(self, request):
        if not getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False):
            return super().__call__(request)
        if self.public_read(request):
            # Public views can personalize for authenticated members or bypass
            # CMS restrictions for staff. A preview must always render their
            # anonymous projection, including before primary MFA. Keep the
            # stored login session intact for the separate private admin gate.
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
            response = self.get_response(request)
        else:
            response = self.restricted_response(request)
        response["Cache-Control"] = "no-store, private"
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response


class OperationalMiddleware(PublicPreviewMiddleware):
    """Operational HTTP protections; domain ownership and scoped admin rules stay in views.

    Preserve the global admin login ceiling without trusting forwarding headers.
    Dynamic private responses are never cacheable. Public discovery is a separate
    editorial decision, so this first operational stage remains noindex.
    """
    def __call__(self, request):
        if not getattr(settings, "ANTHEEC_OPERATIONAL", False):
            return self.get_response(request)
        user = request.user
        factor_pending = bool(user.is_authenticated and
            Authority.objects.filter(pk=1, primary_id=user.pk).exists() and
            (not user.is_verified() or request.session.get("authority_epoch") != 0))
        login_paths = {"/health/", "/admin/login/", "/admin/logout/", "/members/logout/",
                       "/security/enroll/", "/security/challenge/"}
        if factor_pending and request.path_info not in login_paths:
            if self.public_read(request):
                # Password-only primary sessions must not unlock CMS login
                # restrictions or personalized/private public-view branches.
                from django.contrib.auth.models import AnonymousUser
                request.user = AnonymousUser()
                response = self.get_response(request)
            else:
                response = redirect("/security/challenge/")
        else:
            response = self.get_response(request)
        response["Cache-Control"] = "no-store, private"
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(settings, "ANTHEEC_OPERATIONAL", False):
            return None
        if request.path_info != "/admin/login/" or request.method != "POST":
            return None
        # Reuse the same post-CSRF budget with no synthetic preview setting.
        return self.login_budget()
