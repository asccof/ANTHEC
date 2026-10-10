from io import StringIO
from unittest import skipUnless
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from . import services as s, membership_admin_services as a, test_concurrency as helpers
from .tests import synthetic_user, administrative_request
from .models import Authority, Person, Application, Membership, Document


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class MembershipAdminConcurrencyTests(TransactionTestCase):
    concurrent = helpers.ConcurrentPolicyTests.concurrent

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
        self.person = Person.objects.create(
            full_name="Synthetic", verification_notice_at=timezone.now()
        )

    def test_approval_and_rejection_are_one_decision(self):
        app = s.create_application(self.person, "founder")
        result = self.concurrent(
            lambda request, index: (s.approve_membership if index == 0 else a.reject)(
                request, key=str(index), application_id=app.pk, reason="Synthetic"
            )
        )
        self.assertEqual(sorted(r[0] for r in result), ["conflict", "ok"])
        app.refresh_from_db()
        count = 1 if app.state == "approved" else 0
        self.assertEqual(Membership.objects.count(), count)
        self.assertEqual(Document.objects.count(), count)

    def test_two_accounts_cannot_claim_same_legacy_record(self):
        users = [synthetic_user("synthetic-a"), synthetic_user("synthetic-b")]
        result = self.concurrent(
            lambda request, index: a.link_person(
                request,
                key=str(index),
                person_id=self.person.pk,
                user_id=users[index].pk,
                reason="Synthetic verified identity",
            )
        )
        self.assertEqual(sorted(r[0] for r in result), ["conflict", "ok"])
        self.person.refresh_from_db()
        self.assertIn(self.person.user_id, [u.pk for u in users])
        self.assertEqual(Person.objects.count(), 1)
