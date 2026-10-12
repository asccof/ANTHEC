import base64
import hashlib
import io
from datetime import timedelta
from unittest.mock import patch
from PIL import Image
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client
from django.utils import timezone
from pypdf import PdfReader
from . import services as s, certificate_assets as a, pdf_design as design, pdf_services as pdf
from .models import Authority, CertificateAsset, Person, Accreditation, Document, PDFArtifact, Audit, Delegation
from .tests import synthetic_user, administrative_request
from . import tests as fixtures


def raw_fixture(color="blue"):
    # Plain rectangle is an image-integrity fixture, never an imitation of an
    # authentic signature/stamp and never part of the owner proof collection.
    stream = io.BytesIO(); Image.new("RGBA", (600, 300), color).save(stream, "PNG")
    return stream.getvalue()


def approved_test_assets(user, color="blue"):
    body = raw_fixture(color)
    return [CertificateAsset.objects.create(kind=kind, uploaded_by=user, image=s.encrypt({"png": base64.b64encode(body).decode()}), sha256=hashlib.sha256(body).hexdigest(), state="approved", reviewed_by=user, reviewed_at=timezone.now()) for kind in ("signature", "stamp")]


class CertificateAssetTests(TestCase):
    http_login = fixtures.PolicyTests.http_login
    def setUp(self):
        self.admin = synthetic_user("synthetic-primary", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        self.other = synthetic_user("synthetic-delegate", True)
        Delegation.objects.create(user=self.other, active=True)
        self.person = Person.objects.create(full_name="Synthetic Certificate Holder")
        self.acc = Accreditation.objects.create(person=self.person, subject_name=self.person.full_name, kind="individual", starts_on=timezone.localdate(), ends_on=timezone.localdate()+timedelta(days=365))

    def upload(self, kind="signature", key="upload"):
        return a.upload_asset(self.request, key=key, kind=kind, image_data=base64.b64encode(raw_fixture()).decode(), reason="Synthetic image-integrity test")

    def test_primary_mfa_recent_reauthentication_and_replay(self):
        first = self.upload(); self.assertEqual(self.upload(), first)
        self.assertEqual(CertificateAsset.objects.count(), 1)
        with self.assertRaises(PermissionDenied):
            a.upload_asset(administrative_request(self.other), key="delegate", kind="signature", image_data=base64.b64encode(raw_fixture()).decode(), reason="Synthetic")
        self.request.session["reauth_at"] = 0
        with self.assertRaises(PermissionDenied): self.upload(key="stale")
        self.request = administrative_request(self.admin)
        self.admin.is_verified = lambda: False
        with self.assertRaises(PermissionDenied): self.upload(key="no-mfa")

    def test_normalization_validation_review_replacement_and_no_public_exposure(self):
        for value in (b"invalid", raw_fixture()[:50], b"x"*(a.MAX_BYTES+1)):
            with self.assertRaises(ValidationError): a.normalize(io.BytesIO(value))
        row = CertificateAsset.objects.get(serial=self.upload()["asset"])
        self.assertNotIn("iVBOR", row.image)
        a.review_asset(self.request, key="approve", asset_id=row.pk, decision="approved", reason="Synthetic fixture review")
        row.refresh_from_db(); self.assertEqual(row.state, "approved")
        row.image = "changed"
        with self.assertRaises(ValidationError): row.save()
        new = CertificateAsset.objects.get(serial=self.upload(key="replacement")["asset"])
        a.review_asset(self.request, key="approve-replacement", asset_id=new.pk, decision="approved", reason="Synthetic replacement")
        self.assertTrue(Audit.objects.filter(action="certificate.asset.replaced", subject=str(row.serial)).exists())
        self.http_login(user=self.other, epoch=Delegation.objects.get(user=self.other).epoch)
        self.assertEqual(self.client.get(f"/private-certificate-assets/{new.serial}/").status_code, 404)
        self.assertEqual(self.client.get("/operations/certificate-assets/").status_code, 403)
        self.http_login(user=self.admin)
        response = self.client.get(f"/private-certificate-assets/{new.serial}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(Client(enforce_csrf_checks=True).post("/operations/certificate-assets/", {}).status_code, 403)

    def test_pending_assets_proof_does_not_create_an_unsigned_artifact(self):
        doc = s.issue("accreditation_certificate", accreditation=self.acc)
        with self.assertRaises(a.PendingCertificateAssets): pdf.artifact_for(doc.pk, "en")
        self.assertFalse(PDFArtifact.objects.exists())
        body, metadata = design.render(doc, "en", proof=True)
        text = PdfReader(io.BytesIO(body)).pages[0].extract_text()
        self.assertIn("Driss Helali", text); self.assertIn("Awaiting authentic signature", text)
        self.assertEqual(metadata["signing_status"], "pending_authentic_assets")
        self.assertNotIn("criteria", text)
        approved_test_assets(self.admin)
        doc.refresh_from_db()
        with self.assertRaises(a.PendingCertificateAssets): pdf.artifact_for(doc.pk, "en")

    def test_asset_binding_artifact_history_and_formal_reissuance(self):
        sig, stamp = approved_test_assets(self.admin)
        doc = s.issue("accreditation_certificate", accreditation=self.acc)
        artifact = pdf.artifact_for(doc.pk, "en"); original = pdf.bytes_for(artifact)
        self.assertEqual(doc.signature_asset_id, sig.pk)
        new_sig, new_stamp = approved_test_assets(self.admin, "red")
        self.assertEqual(pdf.bytes_for(pdf.artifact_for(doc.pk, "en")), original)
        self.assertEqual(pdf.artifact_for(doc.pk, "fr").metadata["signing_snapshot"]["signature_sha256"], sig.sha256)
        self.assertTrue(Audit.objects.filter(action="certificate.assets.used", subject=str(doc.serial)).exists())
        doc.signature_asset = new_sig
        with self.assertRaises(ValidationError): doc.save()
        with self.assertRaises(ProtectedError): sig.delete()
        replacement = s.issue("accreditation_certificate", accreditation=self.acc, version=2, replaces=doc)
        self.assertEqual(replacement.signature_asset_id, new_sig.pk)
        self.assertEqual(replacement.stamp_asset_id, new_stamp.pk)

    def test_participation_remains_proof_only_and_names_are_localized(self):
        counts = (Document.objects.count(), CertificateAsset.objects.count())
        proof = design.ParticipationProof("Synthetic Participant", "Synthetic Training", "ANTHEC", "2026-10-12", "2026-10-13", "16 hours - synthetic")
        for language, name in (("ar", "إدريس هلالي"), ("fr", "Driss Helali"), ("en", "Driss Helali")):
            body, metadata = design.render_participation_proof(proof, language)
            text = PdfReader(io.BytesIO(body)).pages[0].extract_text()
            if language != "ar": self.assertIn(name, text)
            self.assertIn("NOT ISSUED", text)
            if language == "fr": self.assertIn("Attestation de participation", text)
        self.assertEqual((Document.objects.count(), CertificateAsset.objects.count()), counts)

    def test_primary_http_upload_review_and_csrf(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        client = Client(enforce_csrf_checks=True)
        self.http_login(user=self.admin, client=client)
        url = "/operations/certificate-assets/?lang=fr"
        page = client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(client.post(url, {"action": "upload"}).status_code, 403)
        form = page.context["upload_form"]
        response = client.post(url, {"action": "upload", "key": str(form["key"].value()), "kind": "signature", "reason": "Synthetic authorized fixture", "image": SimpleUploadedFile("synthetic-fixture.png", raw_fixture(), content_type="image/png"), "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)
        row = CertificateAsset.objects.get()
        self.assertEqual(row.state, "pending")
        page = client.get(url); form = page.context["review_form"]
        response = client.post(url, {"action": "review", "key": str(form["key"].value()), "asset_id": row.pk, "decision": "approved", "reason": "Synthetic fixture reviewed", "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db(); self.assertEqual(row.state, "approved")
        self.assertTrue(Audit.objects.filter(action="certificate.asset.approved", subject=str(row.serial)).exists())

    def test_unsigned_legacy_html_is_never_a_certificate_download(self):
        from .documents import printable, render_outbox
        from .models import Outbox
        holder = synthetic_user("synthetic-certificate-owner")
        self.person.user = holder; self.person.save()
        doc = s.issue("accreditation_certificate", accreditation=self.acc)
        credentials = s.decrypt(doc.credentials)
        for language in ("ar", "fr", "en"):
            notice = printable(doc, language)
            for value in (credentials["token"], credentials["code"], str(doc.serial), "<svg"):
                self.assertNotIn(value, notice)
        outbox = Outbox.objects.get(document=doc)
        render_outbox(outbox.pk); outbox.refresh_from_db()
        self.assertEqual(outbox.state, "failed")
        self.assertEqual(outbox.last_error, "pending_assets")
        self.assertFalse(PDFArtifact.objects.exists())
        self.client.force_login(holder)
        response = self.client.get(f"/my-documents/{doc.pk}/?lang=en")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/my-documents/{doc.pk}/pdf/", response["Location"])
        self.assertEqual(self.client.get(response["Location"]).status_code, 409)
        # A historical encrypted HTML snapshot is preserved but never delivered.
        Document.objects.filter(pk=doc.pk).update(rendered=s.encrypt("ARCHIVED-UNSIGNED-HTML"), rendering_state="ready")
        self.assertEqual(self.client.get(f"/my-documents/{doc.pk}/?lang=fr").status_code, 302)
        doc.refresh_from_db(); self.assertEqual(s.decrypt(doc.rendered), "ARCHIVED-UNSIGNED-HTML")
