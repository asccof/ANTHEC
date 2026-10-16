from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from io import StringIO
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from .tests import synthetic_user
from . import member_services as m, services as s
from .models import Person, Application


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class ConcurrentMemberTests(TransactionTestCase):
    def setUp(self):
        call_command("seed_policy_prices", stdout=StringIO())
        self.user = synthetic_user("synthetic-concurrent-member")

    def run_concurrently(self, fn):
        barrier = Barrier(2)

        def run(index):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait(timeout=10)
                try:
                    return ("ok", fn(user, index))
                except s.Conflict:
                    return ("conflict", None)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, range(2)))

    def test_parallel_profile_saves_use_one_person(self):
        result = self.run_concurrently(
            lambda user, index: m.update_profile(
                user,
                key=str(index),
                full_name="Synthetic",
                phone="+212600000001",
                profession="Synthetic coach",
                contact="",
                directory_consent=False,
                notice=True,
            )
        )
        self.assertEqual([r[0] for r in result], ["ok", "ok"])
        self.assertEqual(Person.objects.count(), 1)

    def test_parallel_applications_have_one_fixed_quote(self):
        m.update_profile(
            self.user,
            key="profile",
            full_name="Synthetic",
            phone="+212600000001",
            profession="Synthetic coach",
            contact="",
            directory_consent=False,
            notice=True,
        )
        result = self.run_concurrently(
            lambda user, index: m.submit_application(
                user, key=str(index), tier="general", applicant_capacity="interested"
            )
        )
        self.assertEqual(sorted(r[0] for r in result), ["conflict", "ok"])
        self.assertEqual(Application.objects.count(), 1)
