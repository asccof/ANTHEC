import base64
import io
import uuid
from datetime import date
from PIL import Image
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError, PermissionDenied
from . import services as s, portraits as p
from .tests import synthetic_user, administrative_request
from . import tests as fixtures
from .models import Authority, Person, Portrait, Audit, Document, InstitutionalRole


def image_bytes(size=(600, 750), fmt="PNG"):
    out = io.BytesIO()
    Image.new("RGB", size, "#275678").save(out, format=fmt)
    return out.getvalue()


class PortraitTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=self.admin)
        self.request = administrative_request(self.admin)
        self.holder = synthetic_user("synthetic-holder")
        self.other = synthetic_user("synthetic-other")
        self.person = Person.objects.create(
            user=self.holder, full_name="Synthetic Holder"
        )
        self.role = InstitutionalRole.objects.create(
            person=self.person,
            role="president",
            starts_on=date(2026, 1, 1),
            ends_on=date(2028, 3, 17),
            legal_reference="SYNTHETIC-OFFICE",
        )

    def upload(self, user=None, person=None, key=None, raw=None, consent=True):
        result = p.upload_portrait(
            user or self.holder,
            key=key or str(uuid.uuid4()),
            person_id=(person or self.person).pk,
            image_data=base64.b64encode(raw or image_bytes()).decode(),
            consent=consent,
        )
        return Portrait.objects.get(serial=result["portrait"])

    def review(self, row, decision="approved", request=None):
        return p.review_portrait(
            request or self.request,
            key=str(uuid.uuid4()),
            portrait_id=row.pk,
            decision=decision,
            reason="Synthetic review",
        )

    def test_upload_normalization_encryption_and_audit(self):
        row = self.upload()
        self.assertEqual(row.state, "pending")
        self.assertNotIn("/9j/", row.image)
        im = Image.open(io.BytesIO(p.portrait_bytes(row)))
        self.assertEqual(im.size, (600, 750))
        self.assertEqual(im.format, "JPEG")
        self.assertFalse(im.getexif())
        self.assertEqual(
            Audit.objects.get(action="portrait.uploaded").details["consent_version"],
            "portrait-v1",
        )

    def test_invalid_integrity_size_and_frame(self):
        for raw in [
            b"not an image",
            b"x" * (p.MAX_BYTES + 1),
            image_bytes((200, 250)),
            image_bytes((600, 750), "GIF"),
            image_bytes()[:90],
        ]:
            with self.assertRaises(ValidationError):
                p.normalize(io.BytesIO(raw))
        with self.assertRaises(ValidationError):
            self.upload(consent=False)
        self.assertEqual(Portrait.objects.count(), 0)

    def test_original_metadata_discarded_and_orientation(self):
        out = io.BytesIO()
        im = Image.new("RGB", (750, 600), "blue")
        ex = Image.Exif()
        ex[274] = 6
        ex[270] = "PRIVATE-SYNTHETIC-METADATA"
        im.save(out, format="JPEG", exif=ex)
        normalized = p.normalize(io.BytesIO(out.getvalue()))
        clean = Image.open(io.BytesIO(normalized))
        self.assertEqual(clean.size, (600, 750))
        self.assertFalse(clean.getexif())
        self.assertNotIn(b"PRIVATE", normalized)

    def test_ownership_and_guardian_scope(self):
        with self.assertRaises(PermissionDenied):
            self.upload(self.other)
        child = Person.objects.create(
            full_name="Synthetic Minor", minor=True, guardian=self.holder
        )
        self.upload(person=child)
        with self.assertRaises(PermissionDenied):
            self.upload(user=self.other, person=child)

    def test_replay_and_review_once(self):
        key = str(uuid.uuid4())
        a = self.upload(key=key)
        b = self.upload(key=key)
        self.assertEqual(a.pk, b.pk)
        self.review(a)
        with self.assertRaises(s.Conflict):
            self.review(a)

    def test_review_requires_current_authority_and_epoch(self):
        row = self.upload()
        request = administrative_request(self.other)
        with self.assertRaises(PermissionDenied):
            self.review(row, request=request)
        self.request.session["authority_epoch"] = -1
        with self.assertRaises(PermissionDenied):
            self.review(row)

    def test_snapshot_preserved_and_explicit_reissue_uses_new_photo(self):
        old_photo = self.upload()
        self.review(old_photo)
        old = s.issue("president_card", institutional_role=self.role)
        new_photo = self.upload(raw=image_bytes(fmt="JPEG"))
        self.review(new_photo)
        old.refresh_from_db()
        self.assertEqual(old.portrait_id, old_photo.pk)
        self.assertEqual(p.portrait_bytes(old.portrait), p.portrait_bytes(old_photo))
        result = s.replace_document(
            self.request,
            key=str(uuid.uuid4()),
            document_id=old.pk,
            reason="Synthetic photo replacement",
        )
        new = Document.objects.get(pk=result["document"])
        self.assertEqual(new.portrait_id, new_photo.pk)
        self.assertEqual(new.replaces_id, old.pk)
        old.refresh_from_db()
        self.assertTrue(old.void)

    def test_missing_or_unapproved_photo_stays_unbound(self):
        old = s.issue("president_card", institutional_role=self.role)
        row = self.upload()
        self.review(row, "rejected")
        self.assertIsNone(old.portrait_id)
        self.assertIsNone(
            s.issue(
                "president_card", institutional_role=self.role, version=2, replaces=old
            ).portrait_id
        )

    def test_private_access_csrf_and_no_public_leak(self):
        row = self.upload()
        url = f"/private-portraits/{row.serial}/"
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.holder)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        doc = s.issue("president_card", institutional_role=self.role)
        self.assertNotIn("portrait", s.public_document(doc))
        self.assertNotIn("image", s.public_document(doc))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.holder)
        self.assertEqual(
            client.post(
                "/members/portrait/",
                {
                    "person_id": self.person.pk,
                    "consent": "on",
                    "key": str(uuid.uuid4()),
                    "photo": SimpleUploadedFile("synthetic.png", image_bytes()),
                },
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get("/private-media/", follow=True).status_code, 404
        )

    def test_localized_upload_and_admin_navigation(self):
        self.client.force_login(self.holder)
        for lang, title in [
            ("ar", "الصورة الشخصية"),
            ("fr", "Portrait personnel"),
            ("en", "Personal portrait"),
        ]:
            self.assertContains(
                self.client.get("/members/portrait/?lang=" + lang), title
            )
        self.http_login()
        for lang in ("ar", "fr", "en"):
            self.assertEqual(
                self.client.get("/operations/portraits/?lang=" + lang).status_code, 200
            )

    def test_http_upload_and_approve(self):
        self.client.force_login(self.holder)
        response = self.client.post(
            "/members/portrait/?lang=fr",
            {
                "person_id": self.person.pk,
                "consent": "on",
                "key": str(uuid.uuid4()),
                "photo": SimpleUploadedFile("synthetic.png", image_bytes()),
            },
        )
        self.assertEqual(response.status_code, 302)
        row = Portrait.objects.get()
        self.http_login()
        response = self.client.post(
            "/operations/portraits/?lang=fr",
            {
                "portrait_id": row.pk,
                "decision": "approved",
                "reason": "Synthetic review",
                "key": str(uuid.uuid4()),
            },
        )
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.state, "approved")

    def test_review_preview_identifier_matches_scoped_choice(self):
        first = self.upload()
        second_person = Person.objects.create(
            user=self.other, full_name="Other Synthetic Holder"
        )
        second = self.upload(user=self.other, person=second_person)
        self.http_login()
        response = self.client.get("/operations/portraits/?lang=en")
        for row in (first, second):
            self.assertContains(
                response, f'<option value="{row.pk}">{row.person.full_name} — {row.serial}</option>', html=True
            )
            from bs4 import BeautifulSoup
            cards = BeautifulSoup(response.content, "html.parser").select(".review-card")
            card = next(card for card in cards if str(row.serial) in card.get_text())
            self.assertIn(row.person.full_name, card.get_text())
            self.assertEqual(card.find("img")["src"], f"/private-portraits/{row.serial}/")

    def test_more_than_100_review_choices_have_matching_previews(self):
        first = self.upload()
        Portrait.objects.bulk_create(
            [
                Portrait(person=self.person, uploaded_by=self.holder, image=first.image)
                for _ in range(101)
            ]
        )
        self.http_login()
        response = self.client.get("/operations/portraits/?lang=en")
        choices = list(response.context["form"].fields["portrait_id"].queryset)
        previews = list(response.context["portraits"])
        self.assertEqual(len(choices), 100)
        self.assertEqual([p.pk for p in choices], [p.pk for p in previews])
        hidden = Portrait.objects.order_by("pk").last()
        response = self.client.post(
            "/operations/portraits/",
            {
                "portrait_id": hidden.pk,
                "decision": "approved",
                "reason": "Synthetic",
                "key": str(uuid.uuid4()),
            },
        )
        self.assertEqual(response.status_code, 400)
        hidden.refresh_from_db()
        self.assertEqual(hidden.state, "pending")
