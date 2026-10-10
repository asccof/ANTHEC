"""Phase 1 acceptance: synthetic roles, existing issuance and administrative UI."""

from datetime import date
from io import StringIO
from unittest.mock import patch
import uuid
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from . import services as s, institutional as i
from .documents import printable, render_outbox
from .institutional_labels import LABELS
from .models import (
    Authority,
    Delegation,
    Person,
    InstitutionalRole,
    Document,
    Outbox,
    Membership,
    Accreditation,
    Payment,
    Refund,
    Audit,
)
from .tests import synthetic_user, administrative_request
from . import tests as policy_fixtures


class InstitutionalTests(TestCase):
    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        self.holder = synthetic_user("synthetic-office-holder")
        self.person = Person.objects.create(
            user=self.holder,
            full_name="Synthetic Office Holder",
            contact="private@example.invalid",
            verification_notice_at=timezone.now(),
        )

    http_login = policy_fixtures.PolicyTests.http_login

    def payload(self, role="president", **overrides):
        result = {
            "person_id": self.person.pk,
            "role": role,
            "starts_on": "2026-10-01",
            "ends_on": None if role == "founder" else "2029-03-17",
            "legal_reference": "PRIVATE-SYNTHETIC-LEGAL-DECISION",
            "reason": "PRIVATE-SYNTHETIC-REASON",
        }
        result.update(overrides)
        return result

    def grant(self, role="president", key=None, **overrides):
        return i.grant(
            self.request,
            key=key or str(uuid.uuid4()),
            **self.payload(role, **overrides),
        )

    def doc(self, role="president", **overrides):
        return Document.objects.get(pk=self.grant(role, **overrides)["document"])

    def test_role_grants_additional_cards_on_one_person_without_changing_membership(
        self,
    ):
        call_command("seed_policy_prices", stdout=StringIO())
        app = s.create_application(self.person, "accredited")
        s.verify_payment(
            self.request,
            key="pay",
            application_id=app.pk,
            amount="3000",
            method="cash",
            proof_reference="Synthetic",
        )
        original = s.approve_membership(
            self.request, key="member", application_id=app.pk, reason="Synthetic"
        )
        for role in ["founder", "president", "vice_president"]:
            self.grant(role)
        self.assertEqual(Person.objects.count(), 1)
        self.assertEqual(
            InstitutionalRole.objects.filter(person=self.person).count(), 3
        )
        self.assertEqual(
            (Membership.objects.count(), Accreditation.objects.count()), (1, 1)
        )
        self.assertEqual(Document.objects.count(), 5)
        for doc in Document.objects.filter(pk__in=original["documents"]):
            self.assertEqual(s.document_status(doc), "active")
        self.assertEqual(len(set(Document.objects.values_list("serial", flat=True))), 5)
        self.assertEqual(
            len(set(Document.objects.values_list("token_digest", flat=True))), 5
        )

    def test_free_founder_permanent_and_no_duplicate_or_annual_renewal(self):
        doc = self.doc("founder")
        row = doc.institutional_role
        self.assertIsNone(row.ends_on)
        with patch("governance.services.today", return_value=date(2100, 1, 1)):
            self.assertEqual(s.document_status(doc), "active")
        self.assertEqual(
            (
                Payment.objects.count(),
                Refund.objects.count(),
                Membership.objects.count(),
            ),
            (0, 0, 0),
        )
        with self.assertRaises(s.Conflict):
            self.grant("founder")
        with self.assertRaises(ValidationError):
            self.grant("founder", person_id=self.person.pk, ends_on="2027-01-01")
        self.assertEqual(Document.objects.count(), 1)

    def test_explicit_recorded_term_and_reference_required_no_duration_default(self):
        for kwargs in [
            {"ends_on": None},
            {"ends_on": "2026-10-01"},
            {"ends_on": "2026-09-30"},
            {"legal_reference": ""},
            {"starts_on": "bad"},
        ]:
            with self.assertRaises(ValidationError):
                self.grant(**kwargs)
        doc = self.doc()
        self.assertEqual(doc.institutional_role.ends_on, date(2029, 3, 17))
        self.assertEqual(Document.objects.count(), 1)

    def test_office_status_before_start_at_end_and_after_end(self):
        doc = self.doc(starts_on="2026-12-10", ends_on="2027-05-04")
        for day, status in [
            (date(2026, 12, 9), "pending"),
            (date(2026, 12, 10), "active"),
            (date(2027, 5, 3), "active"),
            (date(2027, 5, 4), "expired"),
            (date(2029, 1, 1), "expired"),
        ]:
            with patch("governance.services.today", return_value=day):
                self.assertEqual(s.document_status(doc), status)
        self.assertEqual(doc.institutional_role.ends_on, date(2027, 5, 4))

    def test_suspend_restore_cancel_terminate_immediately_preserve_all_history(self):
        doc = self.doc()
        credentials = s.decrypt(doc.credentials)
        role_id = doc.institutional_role_id
        for state, status in [
            ("suspended", "suspended"),
            ("active", "active"),
            ("cancelled", "cancelled"),
            ("terminated", "cancelled"),
        ]:
            i.change_state(
                self.request,
                key=state,
                role_id=role_id,
                state=state,
                reason="Synthetic " + state,
            )
            response = self.client.post("/verify/", {"token": credentials["token"]})
            self.assertEqual(response.json()["status"], status)
        self.assertEqual(InstitutionalRole.objects.count(), 1)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(
            Audit.objects.filter(action__startswith="institutional.").count(), 5
        )
        for state in ["active", "suspended"]:
            with self.assertRaises(s.Conflict):
                i.change_state(
                    self.request,
                    key="undo-" + state,
                    role_id=role_id,
                    state=state,
                    reason="Synthetic",
                )

    def test_cancelled_office_cannot_restore_indirectly_and_founder_can_reactivate(
        self,
    ):
        doc = self.doc()
        i.change_state(
            self.request,
            key="cancel-office",
            role_id=doc.institutional_role_id,
            state="cancelled",
            reason="Synthetic",
        )
        for state in ["active", "suspended"]:
            with self.assertRaises(s.Conflict):
                i.change_state(
                    self.request,
                    key="bypass-" + state,
                    role_id=doc.institutional_role_id,
                    state=state,
                    reason="Synthetic",
                )
        founder = self.doc("founder")
        for state in ["cancelled", "active"]:
            i.change_state(
                self.request,
                key="founder-" + state,
                role_id=founder.institutional_role_id,
                state=state,
                reason="Synthetic",
            )
        founder.refresh_from_db()
        self.assertEqual(s.document_status(founder), "active")
        with self.assertRaises(ValidationError):
            i.change_state(
                self.request,
                key="founder-term",
                role_id=founder.institutional_role_id,
                state="terminated",
                reason="Synthetic",
            )

    def test_replacement_office_invalidates_predecessor_keeps_person_and_dates(self):
        original = self.doc()
        credentials = s.decrypt(original.credentials)
        other = Person.objects.create(
            full_name="Synthetic successor", verification_notice_at=timezone.now()
        )
        result = self.grant(
            person_id=other.pk,
            replaces_role_id=original.institutional_role_id,
            starts_on="2026-10-10",
            ends_on="2030-06-02",
        )
        new = Document.objects.get(pk=result["document"])
        original.refresh_from_db()
        self.assertEqual(
            s.lookup_document(token=credentials["token"])["status"], "cancelled"
        )
        self.assertEqual(
            new.institutional_role.replaces_id, original.institutional_role_id
        )
        self.assertEqual(new.institutional_role.ends_on, date(2030, 6, 2))
        self.assertEqual(
            (
                Person.objects.count(),
                InstitutionalRole.objects.count(),
                Document.objects.count(),
            ),
            (2, 2, 2),
        )
        with self.assertRaises(s.Conflict):
            self.grant(
                person_id=other.pk, replaces_role_id=original.institutional_role_id
            )
        with self.assertRaises(s.Conflict):
            self.grant("vice_president", replaces_role_id=new.institutional_role_id)

    def test_document_replacement_invalidates_old_card_with_new_unique_credentials(
        self,
    ):
        original = self.doc("founder")
        credentials = s.decrypt(original.credentials)
        result = s.replace_document(
            self.request,
            key="replace-card",
            document_id=original.pk,
            reason="Synthetic loss",
        )
        new = Document.objects.get(pk=result["document"])
        self.assertEqual(new.institutional_role_id, original.institutional_role_id)
        self.assertEqual(new.replaces_id, original.pk)
        self.assertEqual(new.version, 2)
        self.assertNotEqual(original.serial, new.serial)
        self.assertNotEqual(original.token_digest, new.token_digest)
        self.assertEqual(
            s.lookup_document(token=credentials["token"])["status"], "cancelled"
        )
        self.assertEqual(
            s.lookup_document(token=s.decrypt(new.credentials)["token"])["status"],
            "active",
        )
        self.assertEqual(
            s.replace_document(
                self.request,
                key="replace-card",
                document_id=original.pk,
                reason="Synthetic loss",
            ),
            result,
        )
        self.assertEqual(InstitutionalRole.objects.count(), 1)

    def test_overlapping_same_person_role_grants_conflict_nonoverlapping_terms_preserved(
        self,
    ):
        self.grant()
        with self.assertRaises(s.Conflict):
            self.grant(starts_on="2028-01-01", ends_on="2030-01-01")
        self.grant(starts_on="2029-03-17", ends_on="2032-09-09")
        self.assertEqual(InstitutionalRole.objects.count(), 2)

    def test_grant_idempotency_and_failure_rolls_back_replacement_and_documents(self):
        first = self.grant(key="same")
        self.assertEqual(self.grant(key="same"), first)
        with self.assertRaises(s.Conflict):
            self.grant(key="same", reason="Different")
        with override_settings(ANTHEEC_DATA_KEY=""):
            with self.assertRaises(ValidationError):
                self.grant(replaces_role_id=first["institutional_role"])
        self.assertEqual(InstitutionalRole.objects.get().state, "active")
        self.assertEqual(
            (
                Document.objects.count(),
                Outbox.objects.count(),
                InstitutionalRole.objects.count(),
            ),
            (1, 1, 1),
        )

    def test_institutional_roles_never_grant_platform_permissions(self):
        for role in ["founder", "president", "vice_president"]:
            self.grant(role)
        self.holder.refresh_from_db()
        self.assertFalse(self.holder.is_staff)
        self.assertFalse(self.holder.is_superuser)
        self.assertEqual(self.holder.groups.count(), 0)
        self.assertFalse(Delegation.objects.filter(user=self.holder).exists())
        self.assertEqual(Authority.objects.get().primary_id, self.admin.pk)
        self.http_login(self.holder)
        self.assertEqual(self.client.get("/operations/institutional/").status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 403)

    def test_public_verification_allowlist_reference_requires_code_and_private_decisions_hidden(
        self,
    ):
        doc = self.doc()
        credentials = s.decrypt(doc.credentials)
        self.assertEqual(
            self.client.post("/verify/", {"serial": str(doc.serial)}).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                "/verify/", {"serial": str(doc.serial), "code": "wrong"}
            ).status_code,
            404,
        )
        response = self.client.post(
            "/verify/", {"serial": str(doc.serial), "code": credentials["code"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {
                "full_name",
                "type",
                "document_type",
                "reference",
                "valid_from",
                "valid_until",
                "status",
            },
        )
        self.assertEqual(response.json()["type"], "president")
        for private in [
            "PRIVATE-SYNTHETIC-LEGAL",
            "PRIVATE-SYNTHETIC-REASON",
            "private@example.invalid",
        ]:
            self.assertNotContains(response, private)
        self.assertIn("no-store", response["Cache-Control"])

    def test_localized_printing_download_ownership_and_outbox_retry(self):
        doc = self.doc("vice_president")
        credentials = s.decrypt(doc.credentials)
        self.client.force_login(self.holder)
        for lang in ["ar", "fr", "en"]:
            response = self.client.get(f"/my-documents/{doc.pk}/?lang={lang}")
            self.assertContains(response, LABELS[lang]["vice_president_card"])
            self.assertContains(response, f'lang="{lang}"')
            self.assertContains(response, credentials["code"])
            for private in ["PRIVATE-SYNTHETIC-LEGAL", "PRIVATE-SYNTHETIC-REASON"]:
                self.assertNotContains(response, private)
        stranger = synthetic_user("synthetic-stranger")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(f"/my-documents/{doc.pk}/").status_code, 404)
        outbox = Outbox.objects.get(document=doc)
        render_outbox(outbox.pk)
        render_outbox(outbox.pk)
        doc.refresh_from_db()
        outbox.refresh_from_db()
        self.assertEqual(outbox.attempts, 1)
        self.assertIn(LABELS["ar"]["vice_president_card"], s.decrypt(doc.rendered))
        self.assertNotIn(credentials["token"], doc.credentials)

    def test_database_constraints_and_history_delete_protection(self):
        doc = self.doc("founder")
        with self.assertRaises(IntegrityError), transaction.atomic():
            InstitutionalRole.objects.create(
                person=self.person,
                role="founder",
                starts_on=date(2026, 10, 10),
                legal_reference="Synthetic",
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            InstitutionalRole.objects.create(
                person=self.person,
                role="president",
                starts_on=date(2026, 10, 10),
                ends_on=None,
                legal_reference="Synthetic",
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Document.objects.create(
                kind="founder_card",
                institutional_role=doc.institutional_role,
                version=1,
                subject_name="Synthetic",
                token_digest="A" * 64,
                code_digest="B" * 64,
                credentials="SYNTHETIC",
            )
        with self.assertRaises(ProtectedError):
            doc.institutional_role.delete()
        with self.assertRaises(ProtectedError):
            self.person.delete()

    def test_interface_anonymous_non_director_mfa_and_revoked_delegate(self):
        url = "/operations/institutional/"
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).url, "/security/challenge/")
        delegate = synthetic_user("synthetic-delegate")
        s.delegate(
            self.request,
            key="delegate",
            user_id=delegate.pk,
            active=True,
            reason="Synthetic",
        )
        self.http_login(delegate, Delegation.objects.get(user=delegate).epoch)
        self.assertEqual(self.client.get(url).status_code, 200)
        s.delegate(
            self.request,
            key="revoke",
            user_id=delegate.pk,
            active=False,
            reason="Synthetic",
        )
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_interface_localized_grant_state_replacement_walkthrough(self):
        self.http_login()
        for lang in ["ar", "fr", "en"]:
            response = self.client.get(f"/operations/institutional/?lang={lang}")
            self.assertContains(response, LABELS[lang]["title"])
            self.assertContains(response, LABELS[lang]["legal_reference"])
        response = self.client.get("/operations/institutional/?lang=en")
        data = self.payload(
            "founder", key=str(response.context["form"].initial["key"]), ends_on=""
        )
        response = self.client.post("/operations/institutional/?lang=en", data)
        self.assertEqual(response.status_code, 302)
        row = InstitutionalRole.objects.get()
        url = response.url
        response = self.client.get(url)
        self.assertContains(response, "Founding Member")
        key = str(response.context["decision"].initial["key"])
        self.assertEqual(
            self.client.post(
                url,
                {
                    "action": "state",
                    "state": "suspended",
                    "reason": "Synthetic suspension",
                    "key": key,
                },
            ).status_code,
            302,
        )
        self.assertEqual(InstitutionalRole.objects.get().state, "suspended")
        response = self.client.get(url)
        key = str(response.context["replacement"].initial["key"])
        old = Document.objects.get()
        self.assertEqual(
            self.client.post(
                url,
                {
                    "action": "replace",
                    "document_id": old.pk,
                    "reason": "Synthetic correction",
                    "key": key,
                },
            ).status_code,
            302,
        )
        old.refresh_from_db()
        self.assertTrue(old.void)
        self.assertEqual(Document.objects.count(), 2)
        self.assertContains(self.client.get(url), "Synthetic suspension")

    def test_interface_csrf_recent_mfa_and_document_origin_scoping(self):
        self.http_login()
        row = InstitutionalRole.objects.get(pk=self.grant()["institutional_role"])
        other = self.doc("founder")
        response = self.client.get(f"/operations/institutional/{row.pk}/")
        key = str(response.context["replacement"].initial["key"])
        self.assertEqual(
            self.client.post(
                f"/operations/institutional/{row.pk}/",
                {
                    "action": "replace",
                    "document_id": other.pk,
                    "reason": "Synthetic",
                    "key": key,
                },
            ).status_code,
            400,
        )
        self.assertEqual(Document.objects.count(), 2)
        session = self.client.session
        session["reauth_at"] -= 301
        session.save()
        response = self.client.get("/operations/institutional/")
        self.assertEqual(response.status_code, 200)
        data = self.payload(
            "vice_president", key=str(response.context["form"].initial["key"])
        )
        self.assertEqual(
            self.client.post("/operations/institutional/", data).status_code, 403
        )
        client = Client(enforce_csrf_checks=True)
        self.http_login(client=client)
        self.assertEqual(
            client.post("/operations/institutional/", data).status_code, 403
        )
        self.assertEqual(InstitutionalRole.objects.count(), 2)

    def test_invalid_ui_dates_and_json_inputs_do_not_create_records(self):
        self.http_login()
        for changes in [
            {"ends_on": ""},
            {"role": "unknown"},
            {"person_id": 99999},
            {"legal_reference": ""},
        ]:
            data = self.payload(key=str(uuid.uuid4()))
            data.update(changes)
            self.assertEqual(
                self.client.post("/operations/institutional/", data).status_code, 400
            )
        self.assertEqual(InstitutionalRole.objects.count(), 0)
        for changes in [
            {"ends_on": None},
            {"role": []},
            {"person_id": True},
            {"legal_reference": None},
        ]:
            data = self.payload(key=str(uuid.uuid4()))
            data.update(changes)
            self.assertEqual(
                self.client.post(
                    "/operations/institutional.grant/",
                    data=data,
                    content_type="application/json",
                ).status_code,
                400,
            )

    def test_verification_notice_and_escaped_ui_names(self):
        self.person.verification_notice_at = None
        self.person.save()
        with self.assertRaises(ValidationError):
            self.grant()
        self.person.verification_notice_at = timezone.now()
        self.person.full_name = "<script>Synthetic</script>"
        self.person.save()
        doc = self.doc()
        self.http_login()
        response = self.client.get(
            f"/operations/institutional/{doc.institutional_role_id}/"
        )
        self.assertNotContains(response, "<script>Synthetic</script>")
        self.assertContains(response, "&lt;script&gt;Synthetic&lt;/script&gt;")
        self.assertNotIn("<script>Synthetic</script>", printable(doc, language="en"))

    def test_mfa_required_for_sensitive_commands_and_suspended_card_reissued_stays_suspended(
        self,
    ):
        doc = self.doc()
        self.request.session["reauth_at"] -= 301
        with self.assertRaises(PermissionDenied):
            self.grant("founder")
        self.request.session["reauth_at"] = timezone.now().timestamp()
        i.change_state(
            self.request,
            key="suspend",
            role_id=doc.institutional_role_id,
            state="suspended",
            reason="Synthetic",
        )
        new = Document.objects.get(
            pk=s.replace_document(
                self.request, key="reissue", document_id=doc.pk, reason="Synthetic"
            )["document"]
        )
        self.assertEqual(s.document_status(new), "suspended")

    def test_public_browser_verification_has_localized_role_state_and_allowlisted_values(
        self,
    ):
        doc = self.doc("founder")
        credentials = s.decrypt(doc.credentials)
        for lang in ["ar", "fr", "en"]:
            response = self.client.post(
                f"/verify/?lang={lang}",
                {"serial": str(doc.serial), "code": credentials["code"]},
                HTTP_ACCEPT="text/html",
            )
            self.assertContains(response, LABELS[lang]["founder_card"])
            self.assertContains(response, LABELS[lang]["active"])
            self.assertContains(response, f'lang="{lang}"')
            self.assertNotContains(response, "PRIVATE-SYNTHETIC")
        self.assertEqual(
            self.client.post(
                "/verify/",
                {"token": credentials["token"]},
                HTTP_ACCEPT="application/json",
            ).json()["document_type"],
            "founder_card",
        )
