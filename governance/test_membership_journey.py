import base64
from django.core.files.uploadedfile import SimpleUploadedFile
from .intake_test_support import intake_payload, signup_payload
from datetime import date
from io import StringIO
from unittest.mock import patch
import uuid
from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from .tests import synthetic_user, administrative_request
from . import services as s, member_services as m, institutional as i, tests as fixtures
from .member_labels import vocabulary
from .models import (
    Authority,
    Person,
    Application,
    Membership,
    Accreditation,
    Document,
    Payment,
    Refund,
    Audit,
)


class MembershipJourneyTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        call_command("seed_policy_prices", stdout=StringIO())
        self.director = Client(enforce_csrf_checks=True)
        self.http_login(client=self.director)
        self.member = Client(enforce_csrf_checks=True)

    def form_post(self, client, url, data, action=None):
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["forms"][action] if action else response.context["form"]
        payload = {"csrfmiddlewaretoken": client.cookies["csrftoken"].value, **data}
        if "key" in form.fields:
            payload["key"] = str(form["key"].value())
        if action:
            payload["action"] = action
        if url.startswith("/members/apply/"):
            payload.update(
                address_category="beneficiary",
                residential_address="Synthetic residence",
                photo_consent="on",
                photo=SimpleUploadedFile(
                    "synthetic.png",
                    base64.b64decode(intake_payload()["image_data"]),
                    content_type="image/png",
                ),
            )
        return client.post(url, payload)

    def create_app(self, tier="accredited"):
        self.assertEqual(
            self.form_post(self.member, '/members/signup/?lang=en',
                signup_payload('synthetic-journey', tier=tier, full_name='Synthetic Journey',
                               contact='journey@example.invalid')).status_code, 302)
        return Application.objects.get()

    def admin_post(self, app, action, **data):
        return self.form_post(
            self.director, f"/operations/membership/{app.pk}/?lang=fr", data, action
        )

    def approve(self, app):
        if app.intake_portrait_id and app.intake_portrait.state == "pending":
            from .portraits import review_portrait

            review_portrait(
                administrative_request(self.admin),
                key=str(uuid.uuid4()),
                portrait_id=app.intake_portrait_id,
                decision="approved",
                reason="Synthetic portrait accepted",
            )
        if app.quote:
            self.assertEqual(
                self.admin_post(
                    app,
                    "payment",
                    amount=str(app.quote),
                    method="transfer",
                    proof_reference="PRIVATE-SYNTHETIC-PROOF",
                ).status_code,
                302,
            )
        self.assertEqual(
            self.admin_post(
                app, "approve", reason="PRIVATE-SYNTHETIC-APPROVAL"
            ).status_code,
            302,
        )
        return Membership.objects.get(application=app)

    def test_full_csrf_journey_early_late_renewal_receipts_documents_and_institutional_integration(
        self,
    ):
        with patch("governance.services.today", return_value=date(2026, 10, 10)):
            app = self.create_app()
            first = self.approve(app)
            original = list(Document.objects.all())
            self.assertEqual(len(original), 2)
            person = Person.objects.get()
            i.grant(
                administrative_request(self.admin),
                key="office",
                person_id=person.pk,
                role="president",
                starts_on="2026-10-01",
                ends_on="2029-03-17",
                legal_reference="PRIVATE-SYNTHETIC-OFFICE",
                reason="PRIVATE-SYNTHETIC-REASON",
            )
            for lang in ["ar", "fr", "en"]:
                labels = vocabulary(lang)[1]
                page = self.member.get("/members/documents/?lang=" + lang)
                for text in [
                    labels["gold_card"],
                    labels["professional_certificate"],
                    labels["president_card"],
                ]:
                    self.assertContains(page, text)
                detail = self.member.get(f"/members/applications/{app.pk}/?lang={lang}")
                self.assertContains(detail, str(Payment.objects.get().receipt))
                self.assertNotContains(detail, "PRIVATE-SYNTHETIC")
                for doc in original:
                    response = self.member.get(f"/my-documents/{doc.pk}/?lang={lang}")
                    if doc.kind == "professional_certificate":
                        self.assertEqual(response.status_code, 302)
                        self.assertIn(
                            f"/my-documents/{doc.pk}/pdf/", response["Location"]
                        )
                        self.assertEqual(
                            self.member.get(response["Location"]).status_code, 409
                        )
                    else:
                        self.assertContains(response, f'lang="{lang}"')
                        self.assertContains(response, labels[doc.kind])
                        self.assertContains(response, labels["association_notice"])
                    credentials = s.decrypt(doc.credentials)
                    public = Client(enforce_csrf_checks=True)
                    public.get("/verify/?lang=" + lang)
                    response = public.post(
                        "/verify/?lang=" + lang,
                        {
                            "serial": str(doc.serial),
                            "code": credentials["code"],
                            "csrfmiddlewaretoken": public.cookies["csrftoken"].value,
                        },
                        HTTP_ACCEPT="text/html",
                    )
                    self.assertContains(response, labels[doc.kind])
                    self.assertNotContains(response, "journey@example.invalid")
                    self.assertNotContains(response, "+212600000001")
                    self.assertNotContains(response, "Synthetic coach")
                    if doc.kind == "professional_certificate":
                        self.assertContains(response, labels["professional"])
            self.assertEqual(
                self.form_post(
                    self.member, "/members/renew/", {"membership_id": first.pk}
                ).status_code,
                302,
            )
            renewal = Application.objects.get(previous=first)
            self.assertEqual(renewal.applicant_capacity, "coach")
            self.assertEqual(renewal.profession_snapshot, "Synthetic coach")
            early = self.approve(renewal)
            self.assertEqual(early.starts_on, first.ends_on)
            self.assertEqual(early.ends_on, date(2028, 10, 10))
            self.assertEqual(
                Accreditation.objects.get(membership=early).ends_on, early.ends_on
            )
            for doc in Document.objects.filter(membership=early):
                self.assertEqual(s.document_status(doc), "pending")
            self.assertEqual(Person.objects.count(), 1)
        with patch("governance.services.today", return_value=date(2030, 2, 28)):
            self.assertEqual(
                self.form_post(
                    self.member, "/members/renew/", {"membership_id": early.pk}
                ).status_code,
                302,
            )
            late_app = Application.objects.get(previous=early)
            late = self.approve(late_app)
            self.assertEqual(late.starts_on, date(2030, 2, 28))
            self.assertEqual(late.ends_on, date(2031, 2, 28))
            self.assertEqual(
                self.admin_post(
                    late_app, "state", state="suspended", reason="Synthetic suspension"
                ).status_code,
                302,
            )
            self.assertContains(
                self.member.get("/members/documents/?lang=en"), "Suspended"
            )
            self.assertEqual(
                self.admin_post(
                    late_app, "state", state="active", reason="Synthetic restoration"
                ).status_code,
                302,
            )
            doc = Document.objects.get(membership=late)
            self.assertEqual(
                self.admin_post(
                    late_app,
                    "replace",
                    document_id=doc.pk,
                    reason="Synthetic lost card",
                ).status_code,
                302,
            )
            doc.refresh_from_db()
            self.assertTrue(doc.void)
            self.assertContains(
                self.member.get("/members/documents/?lang=en"), str(doc.serial)
            )
            payment = Payment.objects.get(application=late_app)
            self.assertEqual(
                self.admin_post(
                    late_app,
                    "refund",
                    payment_id=payment.pk,
                    amount="100",
                    approved="yes",
                    reason="Synthetic financial exception",
                ).status_code,
                302,
            )
            self.assertContains(
                self.member.get(f"/members/applications/{late_app.pk}/?lang=en"),
                "100.00",
            )
        for action in [
            "member.account.created",
            "member.profile.created",
            "member.application.submitted",
            "payment.verified",
            "membership.approved",
            "member.renewal.submitted",
            "institutional.granted",
            "membership.suspended",
            "membership.active",
            "document.replaced",
            "refund.decided",
        ]:
            self.assertTrue(Audit.objects.filter(action=action).exists(), action)
        self.assertEqual(
            (Membership.objects.count(), Accreditation.objects.count()), (3, 3)
        )

    def test_rejection_then_resubmission_free_founder_and_no_annual_renewal(self):
        app = self.create_app(tier="general")
        self.assertEqual(
            self.admin_post(
                app, "reject", reason="PRIVATE-SYNTHETIC-REFUSAL"
            ).status_code,
            302,
        )
        self.assertContains(
            self.member.get(f"/members/applications/{app.pk}/?lang=en"), "Rejected"
        )
        self.assertNotContains(
            self.member.get(f"/members/applications/{app.pk}/"), "PRIVATE-SYNTHETIC"
        )
        self.assertEqual(
            self.form_post(
                self.member,
                "/members/apply/",
                {"tier": "founder", "applicant_capacity": "interested"},
            ).status_code,
            302,
        )
        new = Application.objects.exclude(pk=app.pk).get()
        term = self.approve(new)
        self.assertIsNone(term.ends_on)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertFalse(
            self.member.get("/members/renew/")
            .context["form"]
            .fields["membership_id"]
            .queryset.exists()
        )
        self.assertEqual(
            self.form_post(
                self.member, "/members/renew/", {"membership_id": term.pk}
            ).status_code,
            400,
        )
        self.assertEqual(Person.objects.count(), 1)

    def test_renewal_ownership_duplicates_replay_latest_term_and_inactive_state(self):
        app = self.create_app("general")
        first = self.approve(app)
        person = Person.objects.get()
        user = person.user
        result = m.submit_renewal(user, membership_id=first.pk, key="renew")
        self.assertEqual(
            result, m.submit_renewal(user, membership_id=first.pk, key="renew")
        )
        with self.assertRaises(s.Conflict):
            m.submit_renewal(user, membership_id=first.pk, key="duplicate")
        new = Application.objects.get(pk=result["application"])
        latest = self.approve(new)
        self.assertEqual(
            self.form_post(
                self.member, "/members/renew/", {"membership_id": first.pk}
            ).status_code,
            400,
        )
        self.admin_post(new, "state", state="cancelled", reason="Synthetic")
        self.assertEqual(
            self.form_post(
                self.member, "/members/renew/", {"membership_id": latest.pk}
            ).status_code,
            400,
        )
        stranger = synthetic_user("synthetic-stranger")
        self.member.force_login(stranger)
        self.assertEqual(
            self.member.get(f"/members/applications/{app.pk}/").status_code, 404
        )
        self.assertNotContains(
            self.member.get("/members/documents/"), "Synthetic Journey"
        )
        self.assertEqual(
            self.form_post(
                self.member, "/members/renew/", {"membership_id": latest.pk}
            ).status_code,
            400,
        )

    def test_profile_correction_preserves_issued_snapshot_until_admin_reissue(self):
        app = self.create_app("general")
        term = self.approve(app)
        doc = Document.objects.get(membership=term)
        self.assertEqual(
            self.form_post(
                self.member,
                "/members/profile/",
                {
                    "full_name": "Synthetic Corrected",
                    "contact": "corrected@example.invalid",
                    "phone": "+212600000002",
                    "profession": "Synthetic updated coach",
                    "notice": "on",
                },
            ).status_code,
            302,
        )
        doc.refresh_from_db()
        self.assertEqual(doc.subject_name, "Synthetic Journey")
        self.assertEqual(
            self.admin_post(
                app,
                "replace",
                document_id=doc.pk,
                reason="Synthetic verified correction",
            ).status_code,
            302,
        )
        replacement = Document.objects.get(replaces=doc)
        self.assertEqual(replacement.subject_name, "Synthetic Corrected")
        self.assertEqual(
            s.lookup_document(token=s.decrypt(doc.credentials)["token"])["status"],
            "cancelled",
        )
        self.assertEqual(Person.objects.count(), 1)

    def test_guardian_document_read_scope_preserves_managed_identity(self):
        guardian = synthetic_user("synthetic-guardian")
        minor = Person.objects.create(
            guardian=guardian,
            minor=True,
            full_name="Synthetic Dependant",
            verification_notice_at=timezone.now(),
        )
        app = s.create_application(minor, "general")
        s.exempt_fee(
            administrative_request(self.admin),
            key="managed-exemption",
            application_id=app.pk,
            reason="Synthetic",
        )
        s.approve_membership(
            administrative_request(self.admin),
            key="managed",
            application_id=app.pk,
            reason="Synthetic",
        )
        self.member.force_login(guardian)
        self.assertContains(
            self.member.get("/members/documents/"), "Synthetic Dependant"
        )
        self.assertEqual(
            self.member.get(f"/members/applications/{app.pk}/").status_code, 200
        )
        self.assertEqual(
            self.member.get(
                "/my-documents/" + str(Document.objects.get().pk) + "/"
            ).status_code,
            200,
        )
        self.assertFalse(
            self.member.get("/members/renew/")
            .context["form"]
            .fields["membership_id"]
            .queryset.exists()
        )

    def test_administrative_mfa_entry_and_institutional_links_preserve_locale(self):
        pending = Client()
        pending.force_login(self.admin)
        for language in ("ar", "fr", "en"):
            for path in ("/operations/membership/", "/operations/institutional/"):
                response = pending.get(path + "?lang=" + language)
                self.assertRedirects(
                    response,
                    "/security/challenge/?lang=" + language,
                    fetch_redirect_response=False,
                )
                self.assertContains(pending.get(response.url), f'lang="{language}"')
            response = self.director.get("/operations/institutional/?lang=" + language)
            self.assertContains(
                response, f'href="/operations/workspace/?lang={language}"'
            )
        response = pending.get("/operations/membership/?lang=untrusted")
        self.assertEqual(response.url, "/security/challenge/?lang=ar")

    def test_existing_mfa_screens_localized_and_sensitive_password_change_reauth_cleared(
        self,
    ):
        self.http_login()
        for lang in ["ar", "fr", "en"]:
            for path in ["/security/challenge/", "/security/enroll/"]:
                response = self.client.get(path + "?lang=" + lang)
                if path.endswith("enroll/"):
                    self.assertEqual(response.status_code, 403)
                else:
                    self.assertRedirects(response, "/admin/")
                    self.assertIn("no-store", response["Cache-Control"])
        response = self.form_post(
            self.client,
            "/members/password/",
            {
                "old_password": "synthetic-password-123",
                "new_password1": "Cedar-forest-456!pass",
                "new_password2": "Cedar-forest-456!pass",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("reauth_at", self.client.session)
        app = s.create_application(
            Person.objects.create(
                full_name="Synthetic", verification_notice_at=timezone.now()
            ),
            "founder",
        )
        response = self.client.post(
            f"/operations/membership/{app.pk}/",
            {"action": "approve", "key": str(uuid.uuid4()), "reason": "Synthetic"},
        )
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.state, "approved")

    def test_public_site_links_to_localized_membership_interfaces(self):
        call_command("seed_demo", stdout=StringIO())
        for lang in ["ar", "fr", "en"]:
            response = self.member.get(f"/{lang}/")
            self.assertContains(response, f"/members/signup/?lang={lang}")
            self.assertContains(response, f"/members/?lang={lang}")
            self.assertEqual(
                self.member.get("/members/signup/?lang=" + lang).status_code, 200
            )
