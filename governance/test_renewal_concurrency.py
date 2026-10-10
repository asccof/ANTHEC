from io import StringIO
from unittest import skipUnless
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase
from . import services as s, member_services as m, test_member_concurrency as helpers
from .tests import synthetic_user, administrative_request
from .models import Authority, Person, Application


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class RenewalConcurrencyTests(TransactionTestCase):
    run_concurrently = helpers.ConcurrentMemberTests.run_concurrently

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
        self.user = synthetic_user("synthetic-renewal")
        m.update_profile(
            self.user,
            key="profile",
            full_name="Synthetic",
            contact="",
            directory_consent=False,
            notice=True,
        )
        app = s.create_application(Person.objects.get(user=self.user), "general")
        request = administrative_request(self.admin)
        s.exempt_fee(request, key="exempt", application_id=app.pk, reason="Synthetic")
        self.term = s.approve_membership(
            request, key="approve", application_id=app.pk, reason="Synthetic"
        )["membership"]

    def test_parallel_renewals_create_one_application(self):
        result = self.run_concurrently(
            lambda user, index: m.submit_renewal(
                user, key=str(index), membership_id=self.term
            )
        )
        self.assertEqual(sorted(r[0] for r in result), ["conflict", "ok"])
        self.assertEqual(Application.objects.filter(previous_id=self.term).count(), 1)

    def test_parallel_same_key_renewal_returns_same_fixed_quote(self):
        result = self.run_concurrently(
            lambda user, index: m.submit_renewal(
                user, key="same", membership_id=self.term
            )
        )
        self.assertEqual(result[0], result[1])
        self.assertEqual(Application.objects.filter(previous_id=self.term).count(), 1)
