"""Isolated synthetic release-path evidence; never changes live deployment gates."""
import io
import uuid
from datetime import date, timedelta
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.utils import timezone
from pypdf import PdfReader
from . import tests as fixtures, services as s, accreditation_services as cases
from . import test_certificate_assets as asset_fixtures
from .models import Authority, AccreditationCase, Accreditation, Document, PDFArtifact, Membership, Payment, Person, Activity, Registration, Attendance
from .test_deployment import PRIVATE_MIDDLEWARE


class IntegratedReadinessTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = fixtures.synthetic_user("synthetic-readiness-owner", True)
        Authority.objects.create(primary=self.admin)
        self.request = fixtures.administrative_request(self.admin)
        call_command("seed_policy_prices", stdout=io.StringIO())

    def reviewed_case(self, start=None, kind="institution", person_id=None):
        start = start or s.today()
        result = cases.create(self.request, key=str(uuid.uuid4()), kind=kind,
            person_id=person_id, subject_name="" if person_id else "Synthetic Readiness Institution",
            starts_on=start.isoformat(), ends_on=s.year_after(start).isoformat(),
            criteria="PRIVATE-READINESS-CRITERIA", assessment="", fee="125.00", reason="Synthetic draft")
        cases.review(self.request, key=str(uuid.uuid4()), case_id=result["case"], decision="reviewed",
            criteria="PRIVATE-READINESS-CRITERIA", assessment="PRIVATE-READINESS-ASSESSMENT",
            fee="125.00", reason="PRIVATE-READINESS-REVIEW")
        return AccreditationCase.objects.get(pk=result["case"])

    def test_delayed_annual_case_approval_uses_final_approval_date_and_retains_proposal(self):
        approved = date(2028, 2, 29)
        for index, proposed in enumerate((date(2026, 1, 31), date(2030, 1, 31))):
            with self.subTest(proposed=proposed):
                row = self.reviewed_case(proposed)
                with patch("governance.services.today", return_value=approved):
                    result = cases.approve(self.request, key=f"delayed-annual-{index}", case_id=row.pk, reason="Synthetic approval")
                acc = Accreditation.objects.get(pk=result["accreditation"])
                self.assertEqual(acc.starts_on, approved)
                self.assertEqual(acc.ends_on, date(2029, 2, 28))
                row.refresh_from_db()
                self.assertEqual((row.starts_on, row.ends_on), (acc.starts_on, acc.ends_on))
                from .models import Audit
                event = Audit.objects.get(action="accreditation.case.approved", subject=str(row.pk))
                self.assertEqual(event.details["proposed_starts_on"], proposed.isoformat())
                self.assertEqual(event.details["proposed_ends_on"], s.year_after(proposed).isoformat())
                self.http_login()
                history = self.client.get(f"/operations/accreditation/{row.pk}/?lang=en")
                self.assertContains(history, proposed.isoformat())
                self.assertContains(history, "Effective dates")

    def test_direct_individual_approval_anchors_year_but_course_keeps_approved_duration(self):
        person = Person.objects.create(full_name="Synthetic Annual Applicant", verification_notice_at=timezone.now())
        with patch("governance.services.today", return_value=date(2028, 2, 29)):
            annual = s.approve_accreditation(self.request, key="annual-date", kind="individual", person_id=person.pk,
                subject_name="", starts_on="2026-10-10", ends_on="2027-10-10", reason="Synthetic")
            course = s.approve_accreditation(self.request, key="course-date", kind="course", person_id=None,
                subject_name="Synthetic approved course", starts_on="2028-03-05", ends_on="2028-03-12", reason="Synthetic")
        acc = Accreditation.objects.get(pk=annual["accreditation"])
        self.assertEqual((acc.starts_on, acc.ends_on), (date(2028,2,29), date(2029,2,28)))
        acc = Accreditation.objects.get(pk=course["accreditation"])
        self.assertEqual((acc.starts_on, acc.ends_on), (date(2028,3,5), date(2028,3,12)))

    def csrf_post(self, client, url, payload, form_name="form"):
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context[form_name]
        data = {"csrfmiddlewaretoken": client.cookies["csrftoken"].value, **payload}
        if "key" in form.fields:
            data["key"] = str(form["key"].value())
        return client.post(url, data)

    def verify(self, doc):
        public = Client(enforce_csrf_checks=True)
        response = public.get("/verify/?lang=en")
        self.assertEqual(response.status_code, 200)
        return public.post("/verify/?lang=en", {"serial": str(doc.serial),
            "code": s.decrypt(doc.credentials)["code"],
            "csrfmiddlewaretoken": public.cookies["csrftoken"].value}, HTTP_ACCEPT="application/json")

    def test_case_approval_pdf_download_verification_state_and_reissue_join(self):
        row = self.reviewed_case()
        old_signature, _ = asset_fixtures.approved_test_assets(self.admin)
        director = Client(enforce_csrf_checks=True)
        self.http_login(client=director)
        url = f"/operations/accreditation/{row.pk}/?lang=en"
        self.assertEqual(self.csrf_post(director, url,
            {"operation": "approve", "reason": "PRIVATE-READINESS-APPROVAL"}, "approval").status_code, 302)
        row.refresh_from_db()
        doc = Document.objects.get(accreditation=row.accreditation)
        original_pdf = None
        for language in ("ar", "fr", "en"):
            prepared = director.post(f"/my-documents/{doc.pk}/prepare/?lang={language}",
                {"csrfmiddlewaretoken": director.cookies["csrftoken"].value})
            self.assertEqual(prepared.status_code, 302)
            downloaded = director.get(prepared.url)
            self.assertEqual(downloaded.status_code, 200)
            self.assertEqual(downloaded["Content-Type"], "application/pdf")
            self.assertIn("no-store", downloaded["Cache-Control"])
            reader = PdfReader(io.BytesIO(downloaded.content))
            self.assertEqual(len(reader.pages), 1)
            text = reader.pages[0].extract_text()
            for secret in ("PRIVATE-READINESS", "125.00"):
                self.assertNotIn(secret, text)
            if language == "en": original_pdf = downloaded.content
        self.assertEqual(PDFArtifact.objects.filter(document=doc).count(), 3)
        data = self.verify(doc).json()
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["reference"], str(doc.serial))
        self.assertEqual(set(data), {"full_name", "type", "document_type", "reference", "valid_from", "valid_until", "status"})
        outsider = fixtures.synthetic_user("synthetic-readiness-outsider")
        unauthorized = Client(); unauthorized.force_login(outsider)
        self.assertEqual(unauthorized.get(f"/my-documents/{doc.pk}/pdf/").status_code, 404)
        s.change_state(self.request, key="hold-right", model="accreditation", object_id=row.accreditation_id,
                       state="suspended", reason="Synthetic suspension")
        self.assertEqual(self.verify(doc).json()["status"], "suspended")
        self.assertEqual(director.get(f"/my-documents/{doc.pk}/pdf/").status_code, 410)
        s.change_state(self.request, key="resume-right", model="accreditation", object_id=row.accreditation_id,
                       state="active", reason="Synthetic reactivation")
        new_signature, _ = asset_fixtures.approved_test_assets(self.admin, "red")
        from . import pdf_services
        self.assertEqual(pdf_services.bytes_for(PDFArtifact.objects.get(document=doc, language="en")), original_pdf)
        replacement = s.replace_document(self.request, key="replace-right", document_id=doc.pk, reason="Synthetic replacement")
        new = Document.objects.get(pk=replacement["document"])
        doc.refresh_from_db()
        self.assertEqual(doc.signature_asset_id, old_signature.pk)
        self.assertEqual(new.signature_asset_id, new_signature.pk)
        self.assertTrue(doc.void)
        self.assertEqual(self.verify(doc).json()["status"], "cancelled")
        self.assertEqual(self.verify(new).json()["status"], "active")
        self.assertEqual(new.replaces_id, doc.pk)
        self.assertEqual(new.accreditation_id, doc.accreditation_id)
        self.assertEqual(self.verify(new).json()["valid_until"], data["valid_until"])
        self.assertEqual(director.get(f"/my-documents/{doc.pk}/pdf/").status_code, 410)
        self.assertFalse(Membership.objects.exists()); self.assertFalse(Payment.objects.exists())

    def test_guest_guardian_request_invitation_attendance_and_cancellation_join(self):
        guest = fixtures.synthetic_user("synthetic-readiness-guardian")
        adult = Person.objects.create(user=guest, full_name="Synthetic Adult Guest", verification_notice_at=timezone.now())
        minor = Person.objects.create(guardian=guest, minor=True, full_name="Synthetic Child Guest", verification_notice_at=timezone.now())
        activity = Activity.objects.create(title="Synthetic Readiness Activity", starts_on=s.today(), ends_on=s.today()+timedelta(days=1),
            capacity=1, allows_minors=True, consent_version="synthetic-readiness-v1", consent_text="SYNTHETIC GUARDIAN CONSENT")
        participant = Client(enforce_csrf_checks=True); participant.force_login(guest)
        apply = f"/activities/{activity.pk}/?lang=en"
        self.assertEqual(self.csrf_post(participant, apply,
            {"person": minor.pk, "guardian_name": "Synthetic Guardian", "guardian_capacity": "Synthetic legal representative", "consent": "on"}).status_code, 302)
        self.assertEqual(self.csrf_post(participant, apply, {"person": adult.pk}).status_code, 302)
        child_request = Registration.objects.get(person=minor)
        adult_request = Registration.objects.get(person=adult)
        self.assertEqual(child_request.consent_text, activity.consent_text)
        self.assertIsNotNone(child_request.consent_at)
        director = Client(enforce_csrf_checks=True); self.http_login(client=director)
        review = f"/operations/activities/registrations/{child_request.pk}/?lang=en"
        self.assertEqual(self.csrf_post(director, review, {"operation":"accept", "reason":"Synthetic admission"}).status_code, 302)
        invitation = Document.objects.get(registration=child_request)
        self.assertEqual(self.verify(invitation).json()["status"], "active")
        check = director.get(review)
        key = str(check.context["checkin"]["key"].value())
        checkin_payload = {"key":key,"operation":"checkin","csrfmiddlewaretoken":director.cookies["csrftoken"].value}
        self.assertEqual(director.post(review, checkin_payload).status_code, 302)
        self.assertEqual(director.post(review, checkin_payload).status_code, 302)
        self.assertEqual(Attendance.objects.count(), 1)
        adult_review = f"/operations/activities/registrations/{adult_request.pk}/?lang=en"
        self.assertEqual(self.csrf_post(director, adult_review, {"operation":"accept", "reason":"Synthetic capacity check"}).status_code, 400)
        self.assertEqual(self.csrf_post(director, review, {"operation":"cancel", "reason":"Synthetic cancellation"}).status_code, 302)
        self.assertEqual(self.verify(invitation).json()["status"], "cancelled")
        check = director.get(review)
        self.assertEqual(director.post(review, {"operation":"checkin", "key":str(check.context["checkin"]["key"].value()),
            "csrfmiddlewaretoken":director.cookies["csrftoken"].value}).status_code, 400)
        self.assertEqual(self.csrf_post(director, adult_review, {"operation":"accept", "reason":"Synthetic released capacity"}).status_code, 302)
        self.assertEqual(Document.objects.filter(kind="invitation").count(), 2)
        self.assertFalse(Membership.objects.exists()); self.assertFalse(Payment.objects.exists())

    @override_settings(ANTHEEC_OWNER_TESTING=True, MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_private_owner_navigation_and_cross_domain_gates_join(self):
        from .models import Command, Outbox
        from . import pdf_services
        call_command("seed_demo", stdout=io.StringIO())
        call_command("seed_accreditation_demo", stdout=io.StringIO())
        call_command("seed_activity_demo", stdout=io.StringIO())
        row = AccreditationCase.objects.first()
        row.state = "reviewed"; row.save(update_fields=["state"])
        registration = Registration.objects.first()
        paths = ["/admin/", "/ar/", "/fr/", "/en/", "/operations/membership/", "/operations/institutional/",
            "/operations/accreditation/", "/operations/activities/", "/operations/partners/",
            "/operations/directors/", "/operations/pricing/", "/operations/certificate-assets/", "/operations/portraits/"]
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.http_login()
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertIn("noindex", response["X-Robots-Tag"])
        baseline = (Document.objects.count(), Payment.objects.count(), Attendance.objects.count(), Command.objects.count(), Outbox.objects.count())
        for operation in (
            lambda: cases.approve(self.request, key="blocked-case", case_id=row.pk, reason="Synthetic"),
            lambda: s.decide_registration(self.request, key="blocked-invitation", registration_id=registration.pk, accept=True, reason="Synthetic"),
            lambda: s.verify_payment(self.request, key="blocked-payment", application_id=1, amount="100", method="cash", proof_reference="Synthetic"),
            lambda: pdf_services.artifact_for(1, "en"),
        ):
            with self.assertRaises(PermissionDenied): operation()
        self.assertEqual(baseline, (Document.objects.count(), Payment.objects.count(), Attendance.objects.count(), Command.objects.count(), Outbox.objects.count()))
        self.assertEqual(self.client.post("/members/signup/", {}).status_code, 404)
        self.assertEqual(self.client.post("/registrations/request/", {}).status_code, 404)
        self.assertEqual(self.client.get("/verify/").status_code, 404)
