"""Sanitized, read-only technical observations; never a legal or release certificate."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_otp.plugins.otp_totp.models import TOTPDevice
from governance.deployment import workflow_disabled
from governance.models import Authority, RecoveryCode, CertificateAsset


class Command(BaseCommand):
    help = 'Observe hosted release configuration without changing data or disclosing personal data.'
    requires_system_checks = []

    def handle(self, *args, **options):
        hosted = any(getattr(settings, name, False) for name in (
            'ANTHEEC_OWNER_TESTING', 'ANTHEEC_PUBLIC_PREVIEW', 'ANTHEEC_OPERATIONAL'))
        if not hosted:
            raise CommandError('Requires secure hosted mode.')
        try:
            with transaction.atomic():
                postgres = connection.vendor == 'postgresql'
                if postgres:
                    with connection.cursor() as cursor:
                        cursor.execute('SET TRANSACTION READ ONLY')
                authorities = list(Authority.objects.select_related('primary')[:2])
                primary = authorities[0].primary if len(authorities) == 1 and authorities[0].pk == 1 else None
                checks = {
                    'postgresql_read_only_transaction': postgres,
                    'debug_disabled': not settings.DEBUG,
                    'one_active_primary': bool(primary and primary.is_active and primary.is_staff and primary.is_superuser),
                    'primary_has_usable_password': bool(primary and primary.has_usable_password()),
                    'primary_has_confirmed_totp': bool(primary and TOTPDevice.objects.filter(user=primary, confirmed=True).exists()),
                    'primary_has_unused_recovery_code': bool(primary and RecoveryCode.objects.filter(user=primary, used_at=None).exists()),
                    'admin_security_middleware': 'governance.middleware.AdminSecurityMiddleware' in settings.MIDDLEWARE,
                    'secure_session_cookie': settings.SESSION_COOKIE_SECURE,
                    'secure_csrf_cookie': settings.CSRF_COOKIE_SECURE,
                    'https_redirect': settings.SECURE_SSL_REDIRECT,
                    'filesystem_uploads_disabled': settings.STORAGES['default']['BACKEND'] == 'governance.deployment.DisabledMediaStorage',
                    'external_email_disabled': settings.EMAIL_BACKEND == 'django.core.mail.backends.dummy.EmailBackend',
                }
                # Only readiness presence; no names, signatures, device keys or asset bytes.
                assets = {kind: CertificateAsset.objects.filter(kind=kind, state='approved').exists()
                          for kind in ('signature', 'stamp')}
                operational = getattr(settings, 'ANTHEEC_OPERATIONAL', False)
                result = {
                    'scope': 'read-only-technical-release-observations',
                    'mode': 'operational' if operational else ('owner-testing' if getattr(settings, 'ANTHEEC_OWNER_TESTING', False) else 'public-preview'),
                    'checks': checks,
                    'workflows': {name.lower(): not workflow_disabled(name) for name in ('APPLICATIONS', 'PAYMENTS', 'ISSUANCE')},
                    'approved_asset_presence': assets,
                    'unverified': ['privacy_notice_and_versioned_acknowledgements', 'data_processing_formalities',
                                   'retention_and_rights_execution', 'hosted_content_and_prices_acceptance',
                                   'signatory_and_asset_ownership', 'backup_retention_and_key_custody',
                                   'hosted_restore', 'memory_capacity', 'main_branch_protection',
                                   'independent_security_acceptance'],
                    'release_authorized': False,
                }
        except Exception:
            raise CommandError('Observation failed; inspect configuration privately.') from None
        self.stdout.write(json.dumps(result, sort_keys=True))
