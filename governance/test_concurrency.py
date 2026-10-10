"""Real row-lock tests run on PostgreSQL CI, never inferred from SQLite."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from unittest import skipUnless
from django.core.management import call_command
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from . import services as s
from .models import (
    Authority,
    Person,
    Membership,
    Accreditation,
    Document,
    Activity,
    Registration,
    Attendance,
)
from .tests import synthetic_user, administrative_request


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class ConcurrentPolicyTests(TransactionTestCase):
    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
        self.person = Person.objects.create(
            full_name="Synthetic concurrency", verification_notice_at=timezone.now()
        )

    def concurrent(self, fn):
        barrier = Barrier(2)
        admin_id = self.admin.pk

        def run(index):
            close_old_connections()
            try:
                from django.contrib.auth import get_user_model

                user = get_user_model().objects.get(pk=admin_id)
                request = administrative_request(user)
                barrier.wait(timeout=10)
                try:
                    return ("ok", fn(request, index))
                except s.Conflict:
                    return ("conflict", None)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, range(2)))

    def test_simultaneous_approval_same_key_returns_single_atomic_result(self):
        app = s.create_application(self.person, "accredited")
        s.verify_payment(
            administrative_request(self.admin),
            key="pay",
            application_id=app.pk,
            amount="3000",
            method="cash",
            proof_reference="Synthetic",
        )
        results = self.concurrent(
            lambda request, index: s.approve_membership(
                request, key="same", application_id=app.pk, reason="Synthetic"
            )
        )
        self.assertEqual(results[0], results[1])
        self.assertEqual(
            [
                Membership.objects.count(),
                Accreditation.objects.count(),
                Document.objects.count(),
            ],
            [1, 1, 2],
        )

    def test_two_requests_for_last_seat_and_attendance_are_serialized(self):
        activity = Activity.objects.create(
            title="Synthetic last seat",
            starts_on=s.today(),
            ends_on=s.today(),
            capacity=1,
            consent_text="Synthetic",
        )
        people = [
            self.person,
            Person.objects.create(
                full_name="Synthetic second", verification_notice_at=timezone.now()
            ),
        ]
        rows = [
            Registration.objects.create(
                activity=activity, person=person, submitted_by=self.admin
            )
            for person in people
        ]
        results = self.concurrent(
            lambda request, index: s.decide_registration(
                request,
                key=f"seat-{index}",
                registration_id=rows[index].pk,
                accept=True,
                reason="Synthetic",
            )
        )
        self.assertEqual(sorted(x[0] for x in results), ["conflict", "ok"])
        self.assertEqual(Registration.objects.filter(state="confirmed").count(), 1)
        doc = Document.objects.get(kind="invitation")
        checks = self.concurrent(
            lambda request, index: s.check_in(
                request, key=f"check-{index}", document_id=doc.pk
            )
        )
        self.assertEqual(checks[0], checks[1])
        self.assertEqual(Attendance.objects.count(), 1)

    def test_simultaneous_refunds_cannot_exceed_original_payment(self):
        app = s.create_application(self.person, "general")
        payment = s.verify_payment(
            administrative_request(self.admin),
            key="pay",
            application_id=app.pk,
            amount="100",
            method="cash",
            proof_reference="Synthetic",
        )["payment"]
        from django.core.exceptions import ValidationError

        def refund(request, index):
            try:
                return s.decide_refund(
                    request,
                    key=f"refund-{index}",
                    payment_id=payment,
                    amount="60",
                    approved=True,
                    reason="Synthetic",
                )
            except ValidationError:
                raise s.Conflict("Refund cap")

        results = self.concurrent(refund)
        self.assertEqual(sorted(x[0] for x in results), ["conflict", "ok"])
