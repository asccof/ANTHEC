import base64
import io
import uuid
from datetime import date, timedelta
from unittest.mock import patch
from PIL import Image
from django.test import TestCase, Client
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from pypdf import PdfReader
from . import services as s, portraits as p, pdf_design as design, pdf_services as pdf
from .tests import synthetic_user, administrative_request
from . import tests as fixtures
from .models import (
    Authority,
    Person,
    Portrait,
    Document,
    InstitutionalRole,
    PDFArtifact,
    Application,
    Membership,
    Accreditation,
    Outbox,
    Audit,
)


class PDFTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        self.holder = synthetic_user("synthetic-holder")
        self.other = synthetic_user("synthetic-other")
        self.person = Person.objects.create(
            user=self.holder,
            full_name="سامي النموذجي",
            verification_notice_at=timezone.now(),
        )
        raw = io.BytesIO()
        Image.new("RGB", (600, 750), "#265878").save(raw, "PNG")
        r = p.upload_portrait(
            self.holder,
            key="upload",
            person_id=self.person.pk,
            image_data=base64.b64encode(raw.getvalue()).decode(),
            consent=True,
        )
        self.photo = Portrait.objects.get(serial=r["portrait"])
        p.review_portrait(
            self.request,
            key="review",
            portrait_id=self.photo.pk,
            decision="approved",
            reason="Synthetic",
        )
        start = timezone.localdate()
        self.role = InstitutionalRole.objects.create(
            person=self.person,
            role="president",
            starts_on=start,
            ends_on=start + timedelta(days=747),
            legal_reference="SYNTHETIC-OFFICE",
        )
        self.doc = s.issue("president_card", institutional_role=self.role)

    def test_actual_dimensions_embedded_fonts_languages_and_bleed(self):
        for lang in ("ar", "fr", "en"):
            data, meta = design.render(self.doc, lang)
            reader = PdfReader(io.BytesIO(data))
            self.assertEqual(len(reader.pages), 2)
            for page in reader.pages:
                self.assertAlmostEqual(
                    float(page.mediabox.width) * 25.4 / 72, 85.6, places=3
                )
                self.assertAlmostEqual(
                    float(page.mediabox.height) * 25.4 / 72, 53.98, places=3
                )
                self.assertTrue(page["/Resources"]["/Font"])
                for font in page["/Resources"]["/Font"].values():
                    f = font.get_object()
                    f = (
                        f["/DescendantFonts"][0].get_object()
                        if "/DescendantFonts" in f
                        else f
                    )
                    descriptor = f["/FontDescriptor"].get_object()
                    self.assertTrue(
                        "/FontFile2" in descriptor or "/FontFile3" in descriptor
                    )
            self.assertIn(str(self.doc.serial)[:8], reader.pages[0].extract_text())
        data, meta = design.render(self.doc, "ar", bleed=True)
        page = PdfReader(io.BytesIO(data)).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 91.6, places=3)
        self.assertAlmostEqual(float(page.trimbox.width) * 25.4 / 72, 85.6, places=3)
        self.assertAlmostEqual(float(page.trimbox.left) * 25.4 / 72, 3, places=3)

    def test_artifact_replay_snapshot_and_audit(self):
        a = pdf.artifact_for(self.doc.pk, "fr")
        body = pdf.bytes_for(a)
        self.assertEqual(pdf.artifact_for(self.doc.pk, "fr").pk, a.pk)
        self.person.full_name = "Changed Synthetic Profile"
        self.person.save()
        self.assertEqual(pdf.bytes_for(pdf.artifact_for(self.doc.pk, "fr")), body)
        self.assertEqual(PDFArtifact.objects.count(), 1)
        self.assertNotIn("%PDF", a.payload)
        self.assertTrue(Audit.objects.filter(action="document.pdf.rendered").exists())

    def test_private_preview_download_status_and_mfa(self):
        url = f"/my-documents/{self.doc.pk}/pdf/?lang=fr"
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.holder)
        self.assertEqual(
            self.client.post(
                f"/my-documents/{self.doc.pk}/prepare/?lang=fr"
            ).status_code,
            302,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(
            self.client.get(f"/my-documents/{self.doc.pk}/preview/").status_code, 200
        )
        self.assertEqual(PDFArtifact.objects.count(), 1)
        self.role.state = "suspended"
        self.role.save()
        self.assertEqual(self.client.get(url).status_code, 410)
        self.role.state = "active"
        self.role.starts_on = timezone.localdate() - timedelta(days=2)
        self.role.ends_on = timezone.localdate()
        self.role.save()
        self.assertEqual(self.client.get(url).status_code, 410)
        self.role.ends_on = timezone.localdate() + timedelta(days=10)
        self.role.save()
        self.http_login()
        session = self.client.session
        session["reauth_at"] = 0
        session.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_missing_snapshot_never_uses_later_profile_photo(self):
        self.doc.portrait = None
        self.doc.save(update_fields=["portrait"])
        with self.assertRaises(design.PendingPhoto):
            pdf.artifact_for(self.doc.pk)
        self.client.force_login(self.holder)
        self.assertEqual(
            self.client.get(f"/my-documents/{self.doc.pk}/pdf/").status_code, 409
        )
        self.assertFalse(PDFArtifact.objects.exists())

    def test_closed_fetcher_rejects_network_file_and_data(self):
        fetcher = design.AssetFetcher({})
        for url in (
            "http://127.0.0.1/",
            "file:///etc/passwd",
            "data:text/plain,private",
            "https://example.invalid/test",
        ):
            with self.assertRaises(ValueError):
                fetcher.fetch(url)
        self.assertTrue(fetcher.denied)

    def test_certificate_vector_background_and_dimensions(self):
        start = timezone.localdate()
        acc = Accreditation.objects.create(
            person=self.person,
            subject_name=self.person.full_name,
            kind="professional",
            starts_on=start,
            ends_on=start + timedelta(days=365),
        )
        doc = s.issue("professional_certificate", accreditation=acc)
        data, meta = design.render(doc, "ar")
        page = PdfReader(io.BytesIO(data)).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4 / 72, 297, places=3)
        self.assertAlmostEqual(float(page.mediabox.height) * 25.4 / 72, 210, places=3)
        self.assertNotIn(b"<image", (design.ASSETS / "certificate.svg").read_bytes())

    def test_all_existing_categories_keep_person_and_dates(self):
        start = timezone.localdate()
        for category in (
            "general",
            "affiliate",
            "advanced",
            "accredited",
            "founder",
            "honorary",
        ):
            app = Application.objects.create(
                person=self.person,
                tier=category,
                quote=0,
                quoted_on=start,
                state="approved",
            )
            member = Membership.objects.create(
                application=app,
                starts_on=start,
                ends_on=(
                    None
                    if category in {"founder", "honorary"}
                    else start + timedelta(days=365)
                ),
            )
            doc = s.issue(
                "gold_card" if category == "accredited" else "membership_card",
                membership=member,
            )
            body, metadata = design.render(doc, "en")
            self.assertEqual(len(PdfReader(io.BytesIO(body)).pages), 2)
            self.assertEqual(doc.portrait_id, self.photo.pk)
        for role in ("vice_president", "founder"):
            origin = InstitutionalRole.objects.create(
                person=self.person,
                role=role,
                starts_on=start,
                ends_on=None if role == "founder" else start + timedelta(days=441),
                legal_reference="SYNTHETIC-TERM",
            )
            doc = s.issue(role + "_card", institutional_role=origin)
            self.assertEqual(
                len(PdfReader(io.BytesIO(design.render(doc, "ar")[0])).pages), 2
            )
        self.assertEqual(Person.objects.count(), 1)

    def test_long_name_fits_or_fails_closed_without_identity_truncation(self):
        self.doc.subject_name = "عبد الرحمن أمين النموذجي صاحب الاسم الطويل للاختبار"
        self.doc.save()
        body, metadata = design.render(self.doc, "ar")
        self.assertLessEqual(metadata["font_scale"], 1)
        self.doc.subject_name = "W" * 200
        # Explicit layout review rather than silently hiding identity glyphs.
        with self.assertRaises(design.LayoutError):
            design.render(self.doc, "en")

    def test_unsupported_participation_not_invented(self):
        self.doc.kind = "participation_certificate"
        with self.assertRaises(ValidationError):
            design.render(self.doc)

    def test_synthetic_membership_photo_finance_issue_reissue_journey(self):
        from django.core.management import call_command
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import StringIO

        call_command("seed_policy_prices", stdout=StringIO())
        member = Client(enforce_csrf_checks=True)
        member.force_login(self.holder)
        director = Client(enforce_csrf_checks=True)
        self.http_login(client=director)

        def post(client, url, values, action=None):
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            form = (
                response.context["forms"][action]
                if action
                else response.context["form"]
            )
            values = {
                **values,
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
                "key": str(form["key"].value()),
            }
            if action:
                values["action"] = action
            return client.post(url, values)

        raw = io.BytesIO()
        Image.new("RGB", (600, 750), "#215E78").save(raw, "PNG")
        self.assertEqual(
            post(
                member,
                "/members/portrait/?lang=fr",
                {
                    "person_id": self.person.pk,
                    "photo": SimpleUploadedFile("synthetic.png", raw.getvalue()),
                    "consent": "on",
                },
            ).status_code,
            302,
        )
        photo = Portrait.objects.latest("pk")
        self.assertEqual(
            post(
                director,
                "/operations/portraits/?lang=fr",
                {
                    "portrait_id": photo.pk,
                    "decision": "approved",
                    "reason": "Synthetic portrait review",
                },
            ).status_code,
            302,
        )
        app = s.create_application(self.person, "accredited")
        url = f"/operations/membership/{app.pk}/?lang=fr"
        self.assertEqual(
            post(
                director,
                url,
                {
                    "amount": str(app.quote),
                    "method": "transfer",
                    "proof_reference": "SYNTHETIC-TRANSFER",
                },
                "payment",
            ).status_code,
            302,
        )
        self.assertEqual(
            post(
                director, url, {"reason": "Synthetic approval"}, "approve"
            ).status_code,
            302,
        )
        gold = Document.objects.get(membership__application=app, kind="gold_card")
        certificate = Document.objects.get(
            accreditation__membership__application=app, kind="professional_certificate"
        )
        self.assertEqual(gold.portrait_id, photo.pk)
        self.assertIsNone(certificate.portrait_id)

        def prepare(doc, lang):
            member.get("/members/documents/?lang=" + lang)
            return member.post(
                f"/my-documents/{doc.pk}/prepare/?lang=" + lang,
                {"csrfmiddlewaretoken": member.cookies["csrftoken"].value},
            )

        self.assertEqual(prepare(gold, "fr").status_code, 302)
        self.assertEqual(prepare(certificate, "ar").status_code, 302)
        self.assertEqual(
            member.get(f"/my-documents/{gold.pk}/pdf/?lang=fr").status_code, 200
        )
        self.assertEqual(
            member.get(f"/my-documents/{certificate.pk}/pdf/?lang=ar").status_code, 200
        )
        credentials = s.decrypt(gold.credentials)
        self.assertEqual(
            s.lookup_document(serial=str(gold.serial), code=credentials["code"])[
                "status"
            ],
            "active",
        )
        self.assertEqual(
            post(
                director,
                url,
                {"document_id": gold.pk, "reason": "Synthetic reissue"},
                "replace",
            ).status_code,
            302,
        )
        self.assertEqual(member.get(f"/my-documents/{gold.pk}/pdf/").status_code, 410)
        replacement = Document.objects.get(replaces=gold)
        self.assertEqual(prepare(replacement, "en").status_code, 302)
        self.assertEqual(
            member.get(f"/my-documents/{replacement.pk}/pdf/?lang=en").status_code, 200
        )
        self.assertEqual(
            s.lookup_document(serial=str(gold.serial), code=credentials["code"])[
                "status"
            ],
            "cancelled",
        )
        self.assertTrue(Audit.objects.filter(action="document.pdf.downloaded").exists())

    def test_generation_is_post_csrf_and_scoped(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.holder)
        url = f"/my-documents/{self.doc.pk}/prepare/"
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        self.assertEqual(PDFArtifact.objects.count(), 0)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.holder)
        self.assertEqual(
            self.client.get(f"/my-documents/{self.doc.pk}/pdf/").status_code, 409
        )
        self.assertEqual(PDFArtifact.objects.count(), 0)
