from unittest import skipUnless
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.test import TransactionTestCase
from . import services as s, test_concurrency as helpers
from .tests import synthetic_user, administrative_request
from .models import Authority, Delegation, Audit


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class DelegationConcurrencyTests(TransactionTestCase):
    concurrent = helpers.ConcurrentPolicyTests.concurrent

    def setUp(self):
        self.admin = synthetic_user("synthetic-scope-race-owner", True)
        Authority.objects.create(primary=self.admin)
        self.target = synthetic_user("synthetic-scope-race-target")
        s.delegate(
            administrative_request(self.admin),
            key="initial",
            user_id=self.target.pk,
            active=True,
            capabilities=["membership.view"],
            reason="Synthetic",
        )
        self.epoch = Delegation.objects.get(user=self.target).epoch

    def test_parallel_edits_do_not_merge_or_overwrite_stale_scope_selection(self):
        results = self.concurrent(
            lambda request, index: s.delegate(
                request,
                key=f"change-{index}",
                user_id=self.target.pk,
                active=True,
                capabilities=[
                    "membership.view",
                    "membership.approve" if index == 0 else "membership.reject",
                ],
                expected_epoch=self.epoch,
                reason="Synthetic explicit choice",
            )
        )
        self.assertEqual(sorted(r[0] for r in results), ["conflict", "ok"])
        row = Delegation.objects.get(user=self.target)
        self.assertIn(
            row.capabilities,
            [
                ["membership.approve", "membership.view"],
                ["membership.reject", "membership.view"],
            ],
        )
        self.assertEqual(row.epoch, self.epoch + 1)
        self.assertEqual(Audit.objects.filter(action="delegation.changed").count(), 2)

    def test_revoke_serializes_with_current_permission_check(self):
        def operation(request, index):
            if index == 0:
                return s.delegate(
                    request,
                    key="revoke",
                    user_id=self.target.pk,
                    active=False,
                    reason="Synthetic",
                )
            from django.contrib.auth import get_user_model

            target = get_user_model().objects.get(pk=self.target.pk)
            with transaction.atomic():
                try:
                    s.authorize(
                        administrative_request(target, self.epoch),
                        capability="membership.view",
                    )
                    return "authorized-before-revoke"
                except PermissionDenied:
                    return "denied-after-revoke"

        results = self.concurrent(operation)
        self.assertEqual([r[0] for r in results], ["ok", "ok"])
        self.assertIn(
            results[1][1], ["authorized-before-revoke", "denied-after-revoke"]
        )
        row = Delegation.objects.get(user=self.target)
        self.assertFalse(row.active)
        self.assertEqual(row.capabilities, [])
        with transaction.atomic(), self.assertRaises(PermissionDenied):
            s.authorize(
                administrative_request(self.target, self.epoch),
                capability="membership.view",
            )
