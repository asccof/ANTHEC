"""Read-only observations, never a release or recovery certification."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_otp.plugins.otp_totp.models import TOTPDevice
from governance.models import Authority, RecoveryCode


class Command(BaseCommand):
    help = "Print sanitized owner-testing readiness observations without modifying data or exposing secrets."
    requires_system_checks = []

    def handle(self, *args, **options):
        if not getattr(settings, "ANTHEEC_OWNER_TESTING", False):
            raise CommandError("This observation command requires owner-testing mode.")
        try:
            with transaction.atomic():
                postgres = connection.vendor == "postgresql"
                if postgres:
                    with connection.cursor() as cursor:
                        cursor.execute("SET TRANSACTION READ ONLY")
                authorities = list(Authority.objects.select_related("primary")[:2])
                primary = authorities[0].primary if len(authorities) == 1 and authorities[0].pk == 1 else None
                checks = {
                    "postgresql_read_only_transaction": postgres,
                    "one_active_primary": bool(primary and primary.is_active and primary.is_staff and primary.is_superuser),
                    "primary_has_usable_password": bool(primary and primary.has_usable_password()),
                    "primary_has_confirmed_totp": bool(primary and TOTPDevice.objects.filter(user=primary, confirmed=True).exists()),
                    "primary_has_unused_recovery_code": bool(primary and RecoveryCode.objects.filter(user=primary, used_at=None).exists()),
                    "owner_gate_installed": "governance.deployment.OwnerTestingMiddleware" in settings.MIDDLEWARE,
                    "debug_disabled": not settings.DEBUG,
                    "secure_session_cookie": settings.SESSION_COOKIE_SECURE,
                    "secure_csrf_cookie": settings.CSRF_COOKIE_SECURE,
                    "https_redirect": settings.SECURE_SSL_REDIRECT,
                    "external_email_disabled": settings.EMAIL_BACKEND == "django.core.mail.backends.dummy.EmailBackend",
                    "filesystem_media_disabled": settings.STORAGES["default"]["BACKEND"] == "governance.deployment.DisabledMediaStorage",
                }
        except Exception:
            # DB errors can contain connection strings; never echo exception text.
            raise CommandError("Read-only observation failed; inspect configuration privately.") from None
        self.stdout.write(json.dumps({
            "scope": "owner-testing-read-only-observations",
            "checks": checks,
            "unverified": ["owner_possession_of_recovery_codes", "offline_key_custody",
                "backup_availability_and_retention", "restored_data_decryption", "hosted_restore",
                "load_capacity", "independent_legal_and_security_acceptance"],
            "release_authorized": False,
        }, sort_keys=True))
