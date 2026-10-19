from .capabilities import ALL_CAPABILITIES
"""Owner-policy acceptance tests; every identity, payment and activity is synthetic."""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, RequestFactory, override_settings
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from . import services as s
from .models import (
    Authority,
    Delegation,
    Person,
    Price,
    Membership,
    Accreditation,
    Document,
    Outbox,
    Application,
    Command,
    Payment,
    Refund,
    Activity,
    Registration,
    Attendance,
    Audit,
    RecoveryCode,
)
from .documents import printable, render_outbox
from .security import authenticate_factor, consume_attempt


def synthetic_user(name, superuser=False):
    method = (
        get_user_model().objects.create_superuser
        if superuser
        else get_user_model().objects.create_user
    )
    return method(name, name + "@example.invalid", "synthetic-password-123")


def administrative_request(user, epoch=0):
    request = RequestFactory().post("/operations/")
    request.user = user
    # Unit boundary fixture; HTTP tests below use real OTPMiddleware/device sessions.
    user.is_verified = lambda: True
    request.session = {
        "authority_epoch": epoch,
        "reauth_at": timezone.now().timestamp(),
    }
    return request


class PolicyTests(TestCase):
    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
        self.holder = synthetic_user("synthetic-holder")
        self.person = Person.objects.create(
            user=self.holder,
            full_name="Synthetic Person",
            contact="private-contact@example.invalid",
            verification_notice_at=timezone.now(),
        )

    def application(self, tier="accredited", previous=None):
        return s.create_application(self.person, tier, previous)

    def pay(self, app):
        return s.verify_payment(
            self.request,
            key=f"pay-{app.pk}",
            application_id=app.pk,
            amount=str(app.quote),
            method="transfer",
            proof_reference="SYNTHETIC-PROOF",
        )

    def approve(self, app):
        if app.quote:
            self.pay(app)
        return s.approve_membership(
            self.request,
            key=f"approve-{app.pk}",
            application_id=app.pk,
            reason="Synthetic administrative approval",
        )

    def document(self):
        return Document.objects.get(pk=self.approve(self.application())["documents"][0])

    def http_login(self, user=None, epoch=0, client=None):
        user = user or self.admin
        client = client or self.client
        device = TOTPDevice.objects.create(user=user, confirmed=True)
        client.force_login(user)
        session = client.session
        session.update(
            {
                "otp_device_id": device.persistent_id,
                "authority_epoch": epoch,
                "reauth_at": timezone.now().timestamp(),
            }
        )
        session.save()
        return client

    def test_approved_prices_seed_is_idempotent(self):
        call_command("seed_policy_prices", stdout=StringIO())
        self.assertEqual(
            dict(Price.objects.values_list("tier", "amount")),
            {k: Decimal(v) for k, v in s.TIERS.items()},
        )
        self.assertEqual(Price.objects.count(), 6)

    def test_quote_is_fixed_despite_later_price_and_no_promotional_expiry(self):
        app = self.application("affiliate")
        Price.objects.create(tier="affiliate", amount=700, starts_at=timezone.now())
        self.assertEqual(self.application("affiliate").quote, 700)
        app.refresh_from_db()
        self.assertEqual(app.quote, 500)
        self.approve(app)
        self.assertEqual(Payment.objects.get(application=app).amount, 500)

    def test_new_price_is_prospective_and_free_tiers_cannot_be_repriced(self):
        future = timezone.now() + timedelta(days=2)
        s.change_price(
            self.request,
            key="future",
            tier="general",
            amount="200",
            starts_at=future.isoformat(),
        )
        self.assertEqual(self.application("general").quote, 100)
        with self.assertRaises(ValidationError):
            s.change_price(
                self.request,
                key="free-price",
                tier="founder",
                amount="1",
                starts_at=future.isoformat(),
            )

    def test_third_tier_atomically_issues_two_separate_rights_and_documents(self):
        app = self.application()
        result = self.approve(app)
        member = Membership.objects.get(pk=result["membership"])
        accred = Accreditation.objects.get(membership=member)
        self.assertEqual(
            (member.starts_on, member.ends_on), (accred.starts_on, accred.ends_on)
        )
        docs = Document.objects.filter(pk__in=result["documents"])
        self.assertEqual(
            set(docs.values_list("kind", flat=True)),
            {"gold_card", "professional_certificate"},
        )
        self.assertEqual(len(set(docs.values_list("serial", flat=True))), 2)
        self.assertEqual(Outbox.objects.count(), 2)
        self.assertEqual(member.ends_on, s.year_after(s.today()))

    def test_lower_tiers_do_not_grant_automatic_accreditation(self):
        for tier in ["general", "affiliate", "advanced"]:
            result = self.approve(self.application(tier))
            self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(Accreditation.objects.count(), 0)

    def test_free_indefinite_tiers_still_require_explicit_approval(self):
        for tier in ["founder", "honorary"]:
            app = self.application(tier)
            self.assertFalse(Membership.objects.filter(application=app).exists())
            member = Membership.objects.get(pk=self.approve(app)["membership"])
            self.assertIsNone(member.ends_on)
        self.assertEqual(Payment.objects.count(), 0)

    def test_payment_alone_never_creates_right_and_underpayment_is_rejected(self):
        app = self.application()
        self.pay(app)
        self.assertEqual(Membership.objects.count(), 0)
        other = self.application("advanced")
        with self.assertRaises(ValidationError):
            s.approve_membership(
                self.request, key="unpaid", application_id=other.pk, reason="Synthetic"
            )
        self.assertEqual(Document.objects.count(), 0)

    @override_settings(ANTHEEC_DATA_KEY="")
    def test_document_failure_rolls_back_rights_approval_and_command(self):
        app = self.application()
        self.pay(app)
        with self.assertRaises(ValidationError):
            s.approve_membership(
                self.request, key="broken", application_id=app.pk, reason="Synthetic"
            )
        app.refresh_from_db()
        self.assertEqual(app.state, "submitted")
        for model in [Membership, Accreditation, Document, Outbox]:
            self.assertEqual(model.objects.count(), 0)
        self.assertFalse(Command.objects.filter(key="broken").exists())

    def test_replayed_approval_does_not_duplicate_and_changed_payload_conflicts(self):
        app = self.application()
        first = self.approve(app)
        second = s.approve_membership(
            self.request,
            key=f"approve-{app.pk}",
            application_id=app.pk,
            reason="Synthetic administrative approval",
        )
        self.assertEqual(first, second)
        self.assertEqual(Document.objects.count(), 2)
        with self.assertRaises(s.Conflict):
            s.approve_membership(
                self.request,
                key=f"approve-{app.pk}",
                application_id=app.pk,
                reason="Different",
            )

    def test_early_and_late_renewal_dates_and_linked_accreditation(self):
        with patch("governance.services.today", return_value=date(2024, 2, 29)):
            member = Membership.objects.get(
                pk=self.approve(self.application())["membership"]
            )
        self.assertEqual(member.ends_on, date(2025, 2, 28))
        with patch("governance.services.today", return_value=date(2025, 1, 10)):
            renewal = Membership.objects.get(
                pk=self.approve(self.application(previous=member))["membership"]
            )
            self.assertEqual(renewal.starts_on, member.ends_on)
            self.assertEqual(
                s.document_status(Document.objects.get(membership=renewal)), "pending"
            )
        with patch("governance.services.today", return_value=date(2027, 3, 15)):
            late = Membership.objects.get(
                pk=self.approve(self.application(previous=renewal))["membership"]
            )
        self.assertEqual(late.starts_on, date(2027, 3, 15))
        self.assertEqual(late.accreditation.ends_on, late.ends_on)
        self.assertEqual(Membership.objects.count(), 3)

    def test_one_renewal_per_prior_term_and_cross_person_renewal_rejected(self):
        member = Membership.objects.get(
            pk=self.approve(self.application())["membership"]
        )
        self.approve(self.application(previous=member))
        duplicate = self.application(previous=member)
        self.pay(duplicate)
        with self.assertRaises(s.Conflict):
            s.approve_membership(
                self.request,
                key="second-renewal",
                application_id=duplicate.pk,
                reason="Synthetic",
            )
        other = Person.objects.create(
            full_name="Another Synthetic", verification_notice_at=timezone.now()
        )
        with self.assertRaises(ValidationError):
            s.create_application(other, "accredited", member)

    def test_exemption_preserves_quote_and_refund_preserves_financial_history(self):
        app = self.application()
        quote = app.quote
        s.exempt_fee(
            self.request,
            key="exempt",
            application_id=app.pk,
            reason="Synthetic exception",
        )
        s.approve_membership(
            self.request,
            key="approve-exempt",
            application_id=app.pk,
            reason="Synthetic",
        )
        app.refresh_from_db()
        self.assertEqual(app.quote, quote)
        other = self.application("general")
        payment = Payment.objects.get(pk=self.pay(other)["payment"])
        s.decide_refund(
            self.request,
            key="refund",
            payment_id=payment.pk,
            amount="60",
            approved=True,
            reason="Synthetic decision",
        )
        s.decide_refund(
            self.request,
            key="refuse",
            payment_id=payment.pk,
            amount="50",
            approved=False,
            reason="Synthetic refusal",
        )
        with self.assertRaises(ValidationError):
            s.decide_refund(
                self.request,
                key="over-refund",
                payment_id=payment.pk,
                amount="41",
                approved=True,
                reason="Synthetic",
            )
        payment.refresh_from_db()
        self.assertEqual(payment.amount, 100)
        self.assertEqual(Refund.objects.count(), 2)
        with self.assertRaises(ValidationError):
            s.approve_membership(
                self.request,
                key="refunded",
                application_id=other.pk,
                reason="Synthetic",
            )

    def test_suspend_cancel_and_reactivate_update_both_rights_and_future_chain(self):
        member = Membership.objects.get(
            pk=self.approve(self.application())["membership"]
        )
        renewal = Membership.objects.get(
            pk=self.approve(self.application(previous=member))["membership"]
        )
        next_term = Membership.objects.get(
            pk=self.approve(self.application(previous=renewal))["membership"]
        )
        for state in ["suspended", "cancelled", "active"]:
            s.change_state(
                self.request,
                key=state,
                model="membership",
                object_id=member.pk,
                state=state,
                reason="Synthetic reason",
            )
            for term in [member, renewal, next_term]:
                term.refresh_from_db()
                self.assertEqual(term.state, state)
                self.assertEqual(
                    Accreditation.objects.get(membership=term).state, state
                )
        self.assertEqual(Membership.objects.count(), 3)
        self.assertEqual(
            Audit.objects.filter(action__startswith="membership.").count(), 6
        )

    def test_cancelled_membership_cannot_be_bypassed_via_certificate_reactivation(self):
        member = Membership.objects.get(
            pk=self.approve(self.application())["membership"]
        )
        s.change_state(
            self.request,
            key="cancel",
            model="membership",
            object_id=member.pk,
            state="cancelled",
            reason="Synthetic",
        )
        with self.assertRaises(ValidationError):
            s.change_state(
                self.request,
                key="bypass",
                model="accreditation",
                object_id=member.accreditation.pk,
                state="active",
                reason="Synthetic",
            )
        self.assertEqual(
            Accreditation.objects.get(membership=member).state, "cancelled"
        )

    def test_reissue_invalidates_old_credentials_and_preserves_link_and_snapshot(self):
        old = self.document()
        credentials = s.decrypt(old.credentials)
        self.person.full_name = "Corrected Synthetic Name"
        self.person.save()
        result = s.replace_document(
            self.request,
            key="replace",
            document_id=old.pk,
            reason="Synthetic name correction",
        )
        new = Document.objects.get(pk=result["document"])
        old.refresh_from_db()
        self.assertEqual(new.replaces_id, old.pk)
        self.assertEqual(new.version, 2)
        self.assertEqual(
            s.lookup_document(token=credentials["token"])["status"], "cancelled"
        )
        self.assertEqual(
            s.lookup_document(token=credentials["token"])["full_name"],
            "Synthetic Person",
        )
        self.assertEqual(
            s.lookup_document(token=s.decrypt(new.credentials)["token"])["full_name"],
            "Corrected Synthetic Name",
        )
        self.assertNotEqual(old.token_digest, new.token_digest)
        with self.assertRaises(s.Conflict):
            s.replace_document(
                self.request, key="again", document_id=old.pk, reason="Synthetic"
            )

    def test_public_verification_requires_secret_and_has_only_allowlisted_fields(self):
        doc = self.document()
        credentials = s.decrypt(doc.credentials)
        for data in [
            {"serial": str(doc.serial)},
            {"serial": str(doc.serial), "code": "wrong"},
            {"full_name": "Synthetic Person"},
            {"token": "unknown"},
        ]:
            self.assertEqual(self.client.post("/verify/", data).status_code, 404)
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
        self.assertNotContains(response, "private-contact")
        self.assertIn("no-store", response["Cache-Control"])
        s.change_state(
            self.request,
            key="suspend",
            model="membership",
            object_id=doc.membership_id,
            state="suspended",
            reason="PRIVATE-REASON",
        )
        response = self.client.post("/verify/", {"token": credentials["token"]})
        self.assertEqual(response.json()["status"], "suspended")
        self.assertNotContains(response, "PRIVATE-REASON")

    def test_verification_throttling_and_csrf(self):
        for _ in range(30):
            self.assertEqual(
                self.client.post("/verify/", {"token": "bad"}).status_code, 404
            )
        self.assertEqual(
            self.client.post("/verify/", {"token": "bad"}).status_code, 429
        )
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post("/verify/", {"token": "bad"})
            .status_code,
            403,
        )

    def test_document_credentials_encrypted_and_outbox_failure_retry_is_idempotent(
        self,
    ):
        doc = self.document()
        credentials = s.decrypt(doc.credentials)
        self.assertNotIn(credentials["token"], doc.credentials)
        outbox = Outbox.objects.get(document=doc)
        with patch(
            "governance.documents.printable", side_effect=ValueError("PRIVATE-ERROR")
        ):
            render_outbox(outbox.pk)
        outbox.refresh_from_db()
        self.assertEqual(outbox.state, "failed")
        self.assertEqual(outbox.last_error, "render_failed")
        render_outbox(outbox.pk)
        render_outbox(outbox.pk)
        doc.refresh_from_db()
        outbox.refresh_from_db()
        self.assertEqual(outbox.attempts, 2)
        self.assertEqual(outbox.state, "rendered")
        self.assertIn("بطاقة عضوية ذهبية", s.decrypt(doc.rendered))
        self.assertNotIn(credentials["code"], doc.rendered)
        self.assertEqual(Document.objects.count(), 2)

    def test_holder_only_download_and_html_escapes_names(self):
        self.person.full_name = "<script>SYNTHETIC</script>"
        self.person.save()
        doc = self.document()
        stranger = synthetic_user("synthetic-stranger")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(f"/my-documents/{doc.pk}/").status_code, 404)
        self.client.force_login(self.holder)
        response = self.client.get(f"/my-documents/{doc.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>SYNTHETIC</script>")
        self.assertContains(response, "&lt;script&gt;SYNTHETIC&lt;/script&gt;")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))

    def test_independent_accreditation_duration_and_subject_validation(self):
        result = s.approve_accreditation(
            self.request,
            key="independent",
            kind="individual",
            person_id=self.person.pk,
            subject_name="",
            starts_on="2026-10-10",
            ends_on="2027-10-10",
            reason="Synthetic criteria accepted",
        )
        self.assertIsNone(
            Accreditation.objects.get(pk=result["accreditation"]).membership_id
        )
        self.assertEqual(Membership.objects.count(), 0)
        with self.assertRaises(ValidationError):
            s.approve_accreditation(
                self.request,
                key="bad-duration",
                kind="institution",
                person_id=None,
                subject_name="Synthetic institution",
                starts_on="2026-10-10",
                ends_on="2028-10-10",
                reason="Synthetic",
            )
        s.approve_accreditation(
            self.request,
            key="course",
            kind="course",
            person_id=None,
            subject_name="Synthetic course",
            starts_on="2026-10-10",
            ends_on="2026-10-15",
            reason="Synthetic approved duration",
        )

    def test_single_primary_and_only_primary_manages_delegates(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Authority.objects.create(pk=2, primary=self.holder)
        delegate = synthetic_user("synthetic-delegate")
        s.delegate(
            self.request,
            key="delegate",
            user_id=delegate.pk,
            active=True, capabilities=list(ALL_CAPABILITIES),
            reason="Synthetic mandate",
        )
        epoch = Delegation.objects.get(user=delegate).epoch
        request = administrative_request(delegate, epoch)
        with self.assertRaises(PermissionDenied):
            s.delegate(
                request,
                key="manage-other",
                user_id=self.holder.pk,
                active=True, capabilities=list(ALL_CAPABILITIES),
                reason="Synthetic",
            )
        with self.assertRaises(ValidationError):
            s.delegate(
                self.request,
                key="primary",
                user_id=self.admin.pk,
                active=False,
                reason="Synthetic",
            )
        with self.assertRaises(ValidationError):
            s.delegate(
                self.request,
                key="boolean",
                user_id=delegate.pk,
                active="false",
                reason="Synthetic",
            )
        self.assertEqual(Authority.objects.get().primary_id, self.admin.pk)

    def test_revocation_and_regrant_invalidates_previous_sessions_and_command_replays(
        self,
    ):
        user = synthetic_user("synthetic-delegate")
        s.delegate(
            self.request, key="grant", user_id=user.pk, active=True, capabilities=list(ALL_CAPABILITIES), reason="Synthetic"
        )
        request = administrative_request(user, Delegation.objects.get(user=user).epoch)
        app = self.application("general")
        result = s.verify_payment(
            request,
            key="paid",
            application_id=app.pk,
            amount="100",
            method="cash",
            proof_reference="Synthetic",
        )
        s.delegate(
            self.request,
            key="revoke",
            user_id=user.pk,
            active=False,
            reason="Synthetic",
        )
        with self.assertRaises(PermissionDenied):
            s.verify_payment(
                request,
                key="paid",
                application_id=app.pk,
                amount="100",
                method="cash",
                proof_reference="Synthetic",
            )
        s.delegate(
            self.request,
            key="regrant",
            user_id=user.pk,
            active=True, capabilities=list(ALL_CAPABILITIES),
            reason="Synthetic",
        )
        with self.assertRaises(PermissionDenied):
            s.verify_payment(
                request,
                key="paid",
                application_id=app.pk,
                amount="100",
                method="cash",
                proof_reference="Synthetic",
            )
        self.assertEqual(Payment.objects.count(), 1)

    def test_primary_mfa_and_current_epoch_required_superuser_is_not_authority(
        self,
    ):
        self.request.session["authority_epoch"] = -1
        with self.assertRaises(PermissionDenied):
            self.approve(self.application("founder"))
        self.request.session["authority_epoch"] = 0
        self.admin.is_verified = lambda: False
        with self.assertRaises(PermissionDenied):
            self.approve(self.application("honorary"))
        outsider = synthetic_user("synthetic-superuser", True)
        with self.assertRaises(PermissionDenied):
            s.approve_membership(
                administrative_request(outsider),
                key="outsider",
                application_id=self.application("founder").pk,
                reason="Synthetic",
            )

    def test_http_admin_mfa_gate_and_operational_delegate_permissions(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").url, "/security/challenge/")
        user = synthetic_user("synthetic-delegate")
        s.delegate(
            self.request,
            key="delegate",
            user_id=user.pk,
            active=True, capabilities=list(ALL_CAPABILITIES),
            reason="Synthetic",
        )
        self.http_login(user, Delegation.objects.get(user=user).epoch)
        self.assertEqual(self.client.get("/admin/").url, "/operations/workspace/")
        for url in ["/admin/users/", "/admin/groups/"]:
            self.assertEqual(self.client.get(url).status_code, 403)
        s.delegate(
            self.request,
            key="revoke",
            user_id=user.pk,
            active=False,
            reason="Synthetic",
        )
        self.assertEqual(self.client.get("/admin/").status_code, 403)

    def test_http_operation_validation_csrf_and_revoked_epoch(self):
        self.http_login()
        response = self.client.post(
            "/operations/membership.approve/",
            data="[]",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        client = Client(enforce_csrf_checks=True)
        self.http_login(client=client)
        self.assertEqual(
            client.post(
                "/operations/membership.approve/",
                data="{}",
                content_type="application/json",
            ).status_code,
            403,
        )
        session = self.client.session
        session["authority_epoch"] = -1
        session.save()
        app = self.application("founder")
        self.assertEqual(
            self.client.post(
                "/operations/membership.approve/",
                data={"key": "x", "application_id": app.pk, "reason": "Synthetic"},
                content_type="application/json",
            ).url,
            "/security/challenge/",
        )

    def test_recovery_codes_are_hashed_single_use_and_attempts_are_limited(self):
        TOTPDevice.objects.create(user=self.admin, confirmed=True)
        RecoveryCode.objects.create(
            user=self.admin, digest=s.digest("SYNTHETIC-RECOVERY")
        )
        self.assertIsNotNone(
            authenticate_factor(self.admin, "SYNTHETIC-RECOVERY", True)
        )
        self.assertIsNone(authenticate_factor(self.admin, "SYNTHETIC-RECOVERY", True))
        self.assertEqual(
            [consume_attempt(self.admin) for _ in range(11)], [True] * 10 + [False]
        )

    def test_real_totp_enrollment_password_and_recovery_challenge(self):
        from django_otp.oath import totp

        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get("/security/enroll/"), "otpauth://")
        self.client.post("/security/enroll/", {"password": "wrong"})
        self.assertEqual(TOTPDevice.objects.count(), 0)
        response = self.client.post(
            "/security/enroll/", {"password": "synthetic-password-123"}
        )
        self.assertContains(response, "otpauth://")
        device = TOTPDevice.objects.get(user=self.admin)
        code = totp(
            device.bin_key,
            step=device.step,
            t0=device.t0,
            digits=device.digits,
            drift=device.drift,
        )
        response = self.client.post(
            "/security/enroll/",
            {"password": "synthetic-password-123", "code": str(code)},
        )
        self.assertEqual(RecoveryCode.objects.count(), 8)
        self.assertTrue(TOTPDevice.objects.get().confirmed)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        token = response.context["codes"][0]
        self.client.logout()
        self.client.login(username=self.admin.username, password="synthetic-password-123")
        self.client.post(
            "/security/challenge/",
            {"password": "synthetic-password-123", "code": token, "recovery": "on"},
        )
        self.assertEqual(RecoveryCode.objects.filter(used_at__isnull=False).count(), 1)
        self.assertEqual(
            self.client.post(
                "/security/enroll/", {"password": "synthetic-password-123"}
            ).status_code,
            403,
        )

    def activity(self, capacity=1, minors=True):
        return Activity.objects.create(
            title="Synthetic Activity",
            starts_on=s.today(),
            ends_on=s.today(),
            capacity=capacity,
            allows_minors=minors,
            consent_text="Synthetic guardian consent v1",
        )

    def test_minor_guardian_explicit_consent_admin_acceptance_and_document_access(self):
        activity = self.activity()
        minor = Person.objects.create(
            full_name="Synthetic Minor",
            minor=True,
            guardian=self.holder,
            verification_notice_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            s.register(activity, minor, self.holder)
        with self.assertRaises(ValidationError):
            s.register(
                activity,
                minor,
                self.admin,
                guardian_name="Synthetic",
                guardian_capacity="Parent",
                consent=True,
            )
        row = s.register(
            activity,
            minor,
            self.holder,
            guardian_name="Synthetic Guardian",
            guardian_capacity="Parent",
            consent=True,
        )
        self.assertEqual(row.state, "requested")
        self.assertIsNotNone(row.consent_at)
        self.assertEqual(row.consent_text, activity.consent_text)
        self.assertEqual(row.consent_version, "v1")
        self.assertEqual(Document.objects.count(), 0)
        result = s.decide_registration(
            self.request,
            key="minor-accept",
            registration_id=row.pk,
            accept=True,
            reason="Synthetic acceptance",
        )
        doc = Document.objects.get(pk=result["document"])
        self.client.force_login(self.holder)
        self.assertEqual(self.client.get(f"/my-documents/{doc.pk}/").status_code, 200)
        self.assertEqual(s.document_status(doc), "active")

    def test_registration_duplicate_capacity_cancel_and_checkin(self):
        activity = self.activity()
        first = s.register(activity, self.person, self.holder)
        with self.assertRaises(s.Conflict):
            s.register(activity, self.person, self.holder)
        second_person = Person.objects.create(
            user=self.admin,
            full_name="Synthetic second",
            verification_notice_at=timezone.now(),
        )
        second = s.register(activity, second_person, self.admin)
        result = s.decide_registration(
            self.request,
            key="first",
            registration_id=first.pk,
            accept=True,
            reason="Synthetic",
        )
        with self.assertRaises(s.Conflict):
            s.decide_registration(
                self.request,
                key="last-seat",
                registration_id=second.pk,
                accept=True,
                reason="Synthetic",
            )
        attendance = s.check_in(
            self.request, key="check-1", document_id=result["document"]
        )
        self.assertEqual(
            s.check_in(self.request, key="check-2", document_id=result["document"]),
            attendance,
        )
        self.assertEqual(Attendance.objects.count(), 1)
        s.cancel_registration(
            self.request, key="cancel", registration_id=first.pk, reason="Synthetic"
        )
        with self.assertRaises(ValidationError):
            s.check_in(
                self.request, key="check-cancelled", document_id=result["document"]
            )
        s.decide_registration(
            self.request,
            key="released",
            registration_id=second.pk,
            accept=True,
            reason="Synthetic",
        )
        self.assertEqual(Registration.objects.filter(state="confirmed").count(), 1)

    def test_registration_http_rejects_other_profile_and_nonmember_can_request(self):
        activity = self.activity()
        self.client.force_login(self.holder)
        payload = {"person_id": self.person.pk, "activity_id": activity.pk}
        self.assertEqual(
            self.client.post(
                "/registrations/request/", data=payload, content_type="application/json"
            ).status_code,
            201,
        )
        self.assertEqual(Membership.objects.count(), 0)
        other = Person.objects.create(
            user=self.admin,
            full_name="Synthetic Other",
            verification_notice_at=timezone.now(),
        )
        payload["person_id"] = other.pk
        self.assertEqual(
            self.client.post(
                "/registrations/request/", data=payload, content_type="application/json"
            ).status_code,
            403,
        )

    def test_malformed_command_types_are_client_errors_and_duplicate_exemptions_conflict(
        self,
    ):
        self.http_login()
        app = self.application("founder")
        for key, reason, object_id in [
            (123, "Synthetic", app.pk),
            ("null", None, app.pk),
            ("list", [], app.pk),
            ("bool-id", "Synthetic", True),
        ]:
            response = self.client.post(
                "/operations/membership.approve/",
                data={"key": key, "reason": reason, "application_id": object_id},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
        paid = self.application("general")
        s.exempt_fee(
            self.request,
            key="first-exemption",
            application_id=paid.pk,
            reason="Synthetic",
        )
        with self.assertRaises(s.Conflict):
            s.exempt_fee(
                self.request,
                key="second-exemption",
                application_id=paid.pk,
                reason="Synthetic",
            )
        self.assertEqual(Membership.objects.count(), 0)

    def test_minor_consent_requires_real_text_version_and_well_typed_guardian_fields(
        self,
    ):
        minor = Person.objects.create(
            full_name="Synthetic Minor",
            minor=True,
            guardian=self.holder,
            verification_notice_at=timezone.now(),
        )
        activity = self.activity()
        self.client.force_login(self.holder)
        payload = {
            "person_id": minor.pk,
            "activity_id": activity.pk,
            "guardian_name": None,
            "guardian_capacity": "Parent",
            "consent": True,
        }
        self.assertEqual(
            self.client.post(
                "/registrations/request/", data=payload, content_type="application/json"
            ).status_code,
            400,
        )
        activity.consent_text = ""
        activity.save()
        with self.assertRaises(ValidationError):
            s.register(
                activity,
                minor,
                self.holder,
                guardian_name="Synthetic Guardian",
                guardian_capacity="Parent",
                consent=True,
            )
        self.assertEqual(Registration.objects.count(), 0)

    def test_future_invitation_cannot_record_attendance_before_valid_from(self):
        day = date(2026, 10, 10)
        activity = Activity.objects.create(
            title="Synthetic future activity",
            starts_on=day + timedelta(days=2),
            ends_on=day + timedelta(days=3),
            capacity=1,
            consent_text="Synthetic",
        )
        row = s.register(activity, self.person, self.holder)
        result = s.decide_registration(
            self.request,
            key="future-admission",
            registration_id=row.pk,
            accept=True,
            reason="Synthetic",
        )
        doc = Document.objects.get(pk=result["document"])
        with patch("governance.services.today", return_value=day):
            self.assertEqual(s.public_document(doc)["status"], "pending")
            with self.assertRaises(ValidationError):
                s.check_in(self.request, key="too-early", document_id=doc.pk)
        self.assertEqual(Attendance.objects.count(), 0)
        with patch("governance.services.today", return_value=activity.starts_on):
            self.assertEqual(s.document_status(doc), "active")
            s.check_in(self.request, key="on-time", document_id=doc.pk)
        with patch(
            "governance.services.today",
            return_value=activity.ends_on + timedelta(days=1),
        ):
            self.assertEqual(s.document_status(doc), "expired")
            with self.assertRaises(ValidationError):
                s.check_in(self.request, key="too-late", document_id=doc.pk)
        self.assertEqual(Attendance.objects.count(), 1)

    def test_minor_admission_rejects_missing_recorded_consent_snapshot(self):
        minor = Person.objects.create(
            full_name="Synthetic Minor",
            minor=True,
            guardian=self.holder,
            verification_notice_at=timezone.now(),
        )
        row = Registration.objects.create(
            activity=self.activity(),
            person=minor,
            submitted_by=self.holder,
            guardian_name="Synthetic Guardian",
            guardian_capacity="Parent",
            consent_at=timezone.now(),
            consent_text="",
            consent_version="",
        )
        with self.assertRaises(ValidationError):
            s.decide_registration(
                self.request,
                key="missing-snapshot",
                registration_id=row.pk,
                accept=True,
                reason="Synthetic",
            )
        row.refresh_from_db()
        self.assertEqual(row.state, "requested")
        self.assertEqual(Document.objects.count(), 0)
