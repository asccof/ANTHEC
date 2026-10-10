from io import StringIO
import uuid
from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from .tests import synthetic_user, administrative_request
from . import tests as fixtures, services as s, membership_admin_services as a
from .member_labels import vocabulary
from .models import (
    Authority,
    Person,
    Application,
    Membership,
    Accreditation,
    Payment,
    Exemption,
    Refund,
    Audit,
    Document,
    Delegation,
)


class MembershipAdminTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
        self.holder = synthetic_user("synthetic-holder")
        self.person = Person.objects.create(
            user=self.holder,
            full_name="Synthetic Holder",
            verification_notice_at=timezone.now(),
        )
        self.app = s.create_application(self.person, "accredited")
        self.http_login()

    def post(self, action, app=None, **data):
        return self.client.post(
            f"/operations/membership/{(app or self.app).pk}/?lang=fr",
            {"action": action, "key": str(uuid.uuid4()), **data},
        )

    def test_financial_approval_cards_state_and_reissue_workflow(self):
        self.assertEqual(
            self.post("approve", reason="Synthetic approval").status_code, 400
        )
        self.assertEqual(
            self.post(
                "payment",
                amount="1000",
                method="cash",
                proof_reference="PRIVATE-SYNTHETIC-CASH",
            ).status_code,
            302,
        )
        self.assertEqual(
            self.post(
                "payment",
                amount="2000",
                method="transfer",
                proof_reference="PRIVATE-SYNTHETIC-TRANSFER",
            ).status_code,
            302,
        )
        self.assertEqual(
            self.post("approve", reason="PRIVATE-SYNTHETIC-APPROVAL").status_code, 302
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.state, "approved")
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(Accreditation.objects.count(), 1)
        self.assertEqual(
            set(Document.objects.values_list("kind", flat=True)),
            {"gold_card", "professional_certificate"},
        )
        self.assertEqual(self.post("approve", reason="Again").status_code, 400)
        self.assertEqual(
            self.post(
                "state", state="suspended", reason="Synthetic suspension"
            ).status_code,
            302,
        )
        for doc in Document.objects.all():
            self.assertEqual(s.document_status(doc), "suspended")
        old = Document.objects.get(kind="gold_card")
        self.assertEqual(
            self.post(
                "replace", document_id=old.pk, reason="Synthetic correction"
            ).status_code,
            302,
        )
        old.refresh_from_db()
        self.assertTrue(old.void)
        self.assertEqual(Document.objects.count(), 3)
        self.assertEqual(
            self.post(
                "state", state="active", reason="Synthetic reactivation"
            ).status_code,
            302,
        )
        response = self.client.get(f"/operations/membership/{self.app.pk}/")
        for text in [
            "payment.verified",
            "membership.approved",
            "membership.suspended",
            "document.replaced",
            "PRIVATE-SYNTHETIC-CASH",
        ]:
            self.assertContains(response, text)
        self.assertEqual(Payment.objects.count(), 2)

    def test_exemption_and_rejection_preserve_records_and_resubmission(self):
        self.assertEqual(
            self.post("exempt", reason="Synthetic exception").status_code, 302
        )
        self.assertEqual(self.post("exempt", reason="Again").status_code, 400)
        self.assertEqual(
            self.post("approve", reason="Synthetic approved exemption").status_code, 302
        )
        self.assertEqual(Exemption.objects.count(), 1)
        other = s.create_application(self.person, "general")
        s.verify_payment(
            self.request,
            key="pay-other",
            application_id=other.pk,
            amount="100",
            method="cash",
            proof_reference="Synthetic",
        )
        self.assertEqual(
            self.post("reject", app=other, reason="Synthetic refusal").status_code, 302
        )
        other.refresh_from_db()
        self.assertEqual(other.state, "rejected")
        self.assertEqual(Payment.objects.filter(application=other).count(), 1)
        self.assertEqual(
            self.post(
                "approve", app=other, reason="Cannot approve rejected"
            ).status_code,
            400,
        )
        self.assertTrue(
            Audit.objects.filter(
                action="membership.rejected", subject=str(other.pk)
            ).exists()
        )
        self.assertEqual(
            self.post("reject", reason="Cannot reject approved").status_code, 400
        )

    def test_refund_decisions_limits_scoping_and_history(self):
        self.post(
            "payment",
            amount="3000",
            method="transfer",
            proof_reference="PRIVATE-SYNTHETIC-PROOF",
        )
        payment = Payment.objects.get()
        key = str(uuid.uuid4())
        payload = {
            "action": "refund",
            "key": key,
            "payment_id": payment.pk,
            "amount": "800",
            "approved": "yes",
            "reason": "Synthetic partial refund",
        }
        url = f"/operations/membership/{self.app.pk}/"
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertEqual(Refund.objects.count(), 1)
        self.assertEqual(
            self.post(
                "refund",
                payment_id=payment.pk,
                amount="2500",
                approved="yes",
                reason="Over cap",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                "refund",
                payment_id=payment.pk,
                amount="2500",
                approved="no",
                reason="Synthetic rejected refund",
            ).status_code,
            302,
        )
        self.assertEqual(Refund.objects.count(), 2)
        self.assertEqual(Payment.objects.get().amount, payment.amount)
        self.assertEqual(
            self.post("approve", reason="Net funds insufficient").status_code, 400
        )
        other = s.create_application(self.person, "general")
        self.assertEqual(
            self.post(
                "refund",
                app=other,
                payment_id=payment.pk,
                amount="10",
                approved="yes",
                reason="Wrong origin",
            ).status_code,
            400,
        )
        self.assertContains(self.client.get(url), "refund.decided")

    def test_deliberate_legacy_link_preserves_person_documents_no_privileges(self):
        legacy = Person.objects.create(
            full_name="Synthetic Legacy", verification_notice_at=timezone.now()
        )
        app = s.create_application(legacy, "founder")
        s.approve_membership(
            self.request,
            key="legacy",
            application_id=app.pk,
            reason="Synthetic founder",
        )
        target = synthetic_user("synthetic-new-account")
        response = self.client.post(
            "/operations/membership/identities/",
            {
                "key": str(uuid.uuid4()),
                "person_id": legacy.pk,
                "user_id": target.pk,
                "reason": "Synthetic verified account identity",
            },
        )
        self.assertEqual(response.status_code, 302)
        legacy.refresh_from_db()
        self.assertEqual(legacy.user_id, target.pk)
        self.assertEqual(Person.objects.count(), 2)
        self.assertFalse(
            target.is_staff or target.is_superuser or target.groups.exists()
        )
        self.assertTrue(
            Audit.objects.filter(
                action="person.linked", subject=str(legacy.pk)
            ).exists()
        )
        self.client.force_login(target)
        self.assertContains(self.client.get("/members/"), "Synthetic Legacy")
        self.assertEqual(
            self.client.get(f"/my-documents/{Document.objects.get().pk}/").status_code,
            200,
        )
        self.assertEqual(self.client.get("/operations/membership/").status_code, 403)

    def test_link_rejects_record_transfer_duplicate_profile_managed_or_inactive(self):
        from django.core.exceptions import ValidationError

        legacy = Person.objects.create(full_name="Synthetic Legacy")
        for person, user in [
            (self.person, synthetic_user("synthetic-new")),
            (legacy, self.holder),
        ]:
            with self.assertRaises(ValidationError):
                a.link_person(
                    self.request,
                    key=str(uuid.uuid4()),
                    person_id=person.pk,
                    user_id=user.pk,
                    reason="Synthetic",
                )
        legacy.minor = True
        legacy.save(update_fields=["minor"])
        with self.assertRaises(ValidationError):
            a.link_person(
                self.request,
                key="minor",
                person_id=legacy.pk,
                user_id=synthetic_user("synthetic-minor-target").pk,
                reason="Synthetic",
            )
        self.assertEqual(Person.objects.get(pk=self.person.pk).user_id, self.holder.pk)

    def test_authorization_mfa_csrf_locale_private_history(self):
        for language in ["ar", "fr", "en"]:
            for path in [
                "/operations/membership/",
                f"/operations/membership/{self.app.pk}/",
                "/operations/membership/identities/",
            ]:
                response = self.client.get(path + "?lang=" + language)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'lang="{language}"')
                self.assertContains(
                    response,
                    'href="/security/challenge/">'
                    + vocabulary(language)["reauth_link"]
                    + "</a>",
                )
                self.assertIn("no-store", response["Cache-Control"])
        session = self.client.session
        session["reauth_at"] = timezone.now().timestamp() - 600
        session.save()
        self.assertEqual(self.post("reject", reason="Synthetic").status_code, 403)
        csrf = Client(enforce_csrf_checks=True)
        self.http_login(client=csrf)
        self.assertEqual(
            csrf.post(
                f"/operations/membership/{self.app.pk}/", {"action": "reject"}
            ).status_code,
            403,
        )
        self.client.force_login(self.holder)
        self.assertEqual(
            self.client.get(f"/operations/membership/{self.app.pk}/").status_code, 403
        )
        self.client.logout()
        self.assertEqual(self.client.get("/operations/membership/").status_code, 302)

    def test_delegate_revoke_and_scoped_document_replacement(self):
        delegate = synthetic_user("synthetic-delegate")
        s.delegate(
            self.request,
            key="delegate",
            user_id=delegate.pk,
            active=True,
            reason="Synthetic",
        )
        self.http_login(delegate, epoch=Delegation.objects.get(user=delegate).epoch)
        self.assertEqual(self.post("exempt", reason="Synthetic").status_code, 302)
        self.assertEqual(self.post("approve", reason="Synthetic").status_code, 302)
        other = s.create_application(self.person, "founder")
        s.approve_membership(
            self.request, key="other", application_id=other.pk, reason="Synthetic"
        )
        wrong = Document.objects.get(membership__application=other)
        self.assertEqual(
            self.post(
                "replace", document_id=wrong.pk, reason="Wrong scope"
            ).status_code,
            400,
        )
        s.delegate(
            self.request,
            key="revoke",
            user_id=delegate.pk,
            active=False,
            reason="Synthetic",
        )
        self.assertEqual(self.client.get("/operations/membership/").status_code, 403)
