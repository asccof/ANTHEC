"""The shell probe must remain read-only and must not print private values."""
import io
import json
from unittest.mock import patch
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django_otp.plugins.otp_totp.models import TOTPDevice
from . import tests as fixtures
from .models import Authority, RecoveryCode
from .test_deployment import PRIVATE_MIDDLEWARE


@override_settings(ANTHEEC_OWNER_TESTING=True, MIDDLEWARE=PRIVATE_MIDDLEWARE)
class OwnerReadinessTests(TransactionTestCase):
    def setUp(self):
        self.primary = fixtures.synthetic_user("PRIVATE-PROBE-IDENTITY", True)
        Authority.objects.create(primary=self.primary)
        TOTPDevice.objects.create(user=self.primary, confirmed=True, key="ab"*20)
        RecoveryCode.objects.create(user=self.primary, digest="PRIVATE-RECOVERY-DIGEST")

    def probe(self):
        output = io.StringIO()
        call_command("check_owner_readiness", stdout=output)
        return output.getvalue(), json.loads(output.getvalue())

    def test_sanitized_observations_no_domain_writes_and_no_release_claim(self):
        with CaptureQueriesContext(connection) as queries:
            output, result = self.probe()
        for private in (self.primary.username, self.primary.email, self.primary.password, "ab"*20, "PRIVATE-RECOVERY-DIGEST"):
            self.assertNotIn(private, output)
        self.assertFalse(result["release_authorized"])
        self.assertTrue(result["checks"]["one_active_primary"])
        self.assertTrue(result["checks"]["primary_has_confirmed_totp"])
        self.assertTrue(result["checks"]["primary_has_unused_recovery_code"])
        self.assertEqual(result["checks"]["postgresql_read_only_transaction"], connection.vendor == "postgresql")
        sql = [item["sql"].strip().upper() for item in queries]
        self.assertFalse(any(statement.startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")) for statement in sql))
        if connection.vendor == "postgresql":
            self.assertIn("SET TRANSACTION READ ONLY", sql)
        self.assertIn("restored_data_decryption", result["unverified"])

    def test_missing_inactive_or_unrecoverable_primary_is_reported_without_repair(self):
        self.primary.is_active = False; self.primary.save(update_fields=["is_active"])
        TOTPDevice.objects.filter(user=self.primary).update(confirmed=False)
        RecoveryCode.objects.all().delete()
        _, result = self.probe()
        for key in ("one_active_primary", "primary_has_confirmed_totp", "primary_has_unused_recovery_code"):
            self.assertFalse(result["checks"][key])
        Authority.objects.all().delete()
        _, result = self.probe()
        self.assertFalse(result["checks"]["one_active_primary"])
        self.assertFalse(Authority.objects.exists())

    def test_database_exception_is_redacted_and_non_trial_runtime_rejected(self):
        with patch("governance.management.commands.check_owner_readiness.Authority.objects.select_related", side_effect=RuntimeError("PRIVATE-DATABASE-URL")):
            with self.assertRaisesMessage(CommandError, "Read-only observation failed") as caught:
                self.probe()
            self.assertNotIn("PRIVATE-DATABASE-URL", str(caught.exception))
        with override_settings(ANTHEEC_OWNER_TESTING=False):
            with self.assertRaisesMessage(CommandError, "requires owner-testing"):
                self.probe()
