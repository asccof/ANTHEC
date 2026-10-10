from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from . import services


class InstitutionalMigrationTests(TransactionTestCase):
    def test_existing_membership_card_retains_origin_serial_and_credentials(self):
        executor = MigrationExecutor(connection)
        restore_target = executor.loader.graph.leaf_nodes()
        old_target = [("governance", "0001_initial")]
        new_target = [("governance", "0002_institutionalrole_and_more")]
        executor.migrate(old_target)
        try:
            old = executor.loader.project_state(old_target).apps
            person = old.get_model("governance", "Person").objects.create(
                full_name="Synthetic migration holder"
            )
            app = old.get_model("governance", "Application").objects.create(
                person_id=person.pk,
                tier="founder",
                quote=0,
                quoted_on=date(2026, 10, 10),
                state="approved",
            )
            member = old.get_model("governance", "Membership").objects.create(
                application_id=app.pk, starts_on=date(2026, 10, 10)
            )
            encrypted = services.encrypt(
                {"token": "SYNTHETIC-MIGRATION-TOKEN", "code": "SYNTHETIC-CODE"}
            )
            doc = old.get_model("governance", "Document").objects.create(
                membership_id=member.pk,
                kind="membership_card",
                subject_name="Synthetic migration holder",
                token_digest="a" * 64,
                code_digest="b" * 64,
                credentials=encrypted,
            )
            old.get_model("governance", "Outbox").objects.create(document_id=doc.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            new = executor.loader.project_state(new_target).apps
            migrated = new.get_model("governance", "Document").objects.get(pk=doc.pk)
            self.assertEqual(migrated.serial, doc.serial)
            self.assertEqual(migrated.credentials, encrypted)
            self.assertEqual(migrated.membership_id, member.pk)
            self.assertIsNone(migrated.institutional_role_id)
            self.assertEqual(
                new.get_model("governance", "InstitutionalRole").objects.count(), 0
            )
            self.assertEqual(
                new.get_model("governance", "Outbox").objects.get().document_id, doc.pk
            )
        finally:
            MigrationExecutor(connection).migrate(restore_target)
