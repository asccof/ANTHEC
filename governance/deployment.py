"""Temporary deployment restrictions, separate from approved domain policies."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.storage import Storage
from django.db import transaction
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.utils import timezone
from .models import Authority, RateBucket


def require_issuance_enabled():
    if getattr(settings, "ANTHEEC_OWNER_TESTING", False):
        raise PermissionDenied("Document issuance and generation are disabled during owner testing.")


def require_applications_enabled():
    if getattr(settings, "ANTHEEC_OWNER_TESTING", False):
        raise PermissionDenied("Applications and registrations are disabled during owner testing.")


def require_payments_enabled():
    if getattr(settings, "ANTHEEC_OWNER_TESTING", False):
        raise PermissionDenied("Payments and refunds are disabled during owner testing.")


class DisabledMediaStorage(Storage):
    def _open(self, name, mode="rb"):
        raise PermissionDenied("Filesystem media is unavailable during owner testing.")

    def _save(self, name, content):
        raise PermissionDenied("Filesystem uploads are disabled during owner testing.")

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
        if (not getattr(settings, "ANTHEEC_OWNER_TESTING", False) or
                request.path_info != "/admin/login/" or request.method != "POST"):
            return None
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
