from unittest import skipUnless
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from . import institutional as i, services as s, test_concurrency as helpers
from .models import Authority, Person, InstitutionalRole, Document, Outbox
from .tests import synthetic_user, administrative_request


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class InstitutionalConcurrencyTests(TransactionTestCase):
    concurrent = helpers.ConcurrentPolicyTests.concurrent

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.person = Person.objects.create(
            full_name="Synthetic founder", verification_notice_at=timezone.now()
        )

    def grant(self, request, key, role="founder"):
        return i.grant(
            request,
            key=key,
            person_id=self.person.pk,
            role=role,
            starts_on="2026-10-01",
            ends_on=None if role == "founder" else "2029-04-12",
            legal_reference="Synthetic legal record",
            reason="Synthetic",
        )

    def test_simultaneous_founder_command_replay_has_one_card_and_role(self):
        results = self.concurrent(lambda request, index: self.grant(request, "same"))
        self.assertEqual(results[0], results[1])
        self.assertEqual(
            (
                InstitutionalRole.objects.count(),
                Document.objects.count(),
                Outbox.objects.count(),
            ),
            (1, 1, 1),
        )

    def test_different_commands_cannot_duplicate_same_office_term(self):
        results = self.concurrent(
            lambda request, index: self.grant(request, f"office-{index}", "president")
        )
        self.assertEqual(sorted(result[0] for result in results), ["conflict", "ok"])
        self.assertEqual(
            (InstitutionalRole.objects.count(), Document.objects.count()), (1, 1)
        )

    def test_simultaneous_reissue_keeps_one_replacement_and_original_history(self):
        original = self.grant(administrative_request(self.admin), "original")[
            "document"
        ]
        results = self.concurrent(
            lambda request, index: s.replace_document(
                request,
                key=f"reissue-{index}",
                document_id=original,
                reason="Synthetic loss",
            )
        )
        self.assertEqual(sorted(result[0] for result in results), ["conflict", "ok"])
        self.assertTrue(Document.objects.get(pk=original).void)
        self.assertEqual(Document.objects.filter(replaces_id=original).count(), 1)
        self.assertEqual(
            (
                InstitutionalRole.objects.count(),
                Document.objects.count(),
                Outbox.objects.count(),
            ),
            (1, 2, 2),
        )
