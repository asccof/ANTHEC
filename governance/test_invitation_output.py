"""Synthetic invitation output, privacy and lifecycle acceptance."""
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
import qrcode
from django.test import TestCase, Client
from django.utils import timezone
from . import tests as fixtures, services as s
from .documents import printable, render_outbox
from .invitation_labels import vocabulary
from .models import Authority, Person, Activity, Registration, Document, Outbox


class InvitationOutputTests(TestCase):
    def setUp(self):
        self.admin = fixtures.synthetic_user("synthetic-invitation-owner", True)
        Authority.objects.create(primary=self.admin)
        self.request = fixtures.administrative_request(self.admin)
        self.guardian = fixtures.synthetic_user("synthetic-invitation-guardian")
        self.person = Person.objects.create(guardian=self.guardian, minor=True,
            full_name='Synthetic <script>alert(1)</script> Child',
            contact="PRIVATE-CONTACT@example.invalid", verification_notice_at=timezone.now())
        self.activity = Activity.objects.create(title="Synthetic activity", starts_on=s.today(),
            ends_on=s.today()+timedelta(days=1), capacity=2, allows_minors=True,
            consent_version="private-v1", consent_text="PRIVATE-CONSENT")
        self.registration = s.register(self.activity, self.person, self.guardian,
            guardian_name="PRIVATE-GUARDIAN", guardian_capacity="PRIVATE-CAPACITY", consent=True)
        self.registration.state = "confirmed"
        self.registration.save(update_fields=["state"])
        self.doc = s.issue("invitation", registration=self.registration)
        self.client.force_login(self.guardian)

    def test_three_language_private_downloads_preserve_snapshot_and_qr_fragment(self):
        self.person.full_name = "Changed live identity"
        self.person.save(update_fields=["full_name"])
        credentials = s.decrypt(self.doc.credentials)
        for language in ("ar", "fr", "en", "unknown"):
            lang, labels = vocabulary(language)
            with self.subTest(language=language), patch("governance.documents.qrcode.make", wraps=qrcode.make) as make:
                response = self.client.get(f"/my-documents/{self.doc.pk}/?lang={language}")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}"')
                for key in ("invitation", "activity invitation", "valid_until", "active"):
                    self.assertContains(response, labels[key])
                self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
                self.assertContains(response, str(self.doc.serial))
                self.assertContains(response, credentials["code"])
                for private in ("<script>", "Changed live identity", "PRIVATE-CONTACT", "PRIVATE-GUARDIAN", "PRIVATE-CAPACITY", "PRIVATE-CONSENT", "full_name:", "document_type:"):
                    self.assertNotContains(response, private)
                self.assertIn("no-store", response["Cache-Control"])
                self.assertEqual(response["Referrer-Policy"], "no-referrer")
                link = urlsplit(make.call_args.args[0])
                self.assertEqual(link.path, "/verify/")
                self.assertEqual(parse_qs(link.query), {"lang": [lang]})
                self.assertEqual(link.fragment, credentials["token"])
        outsider = Client(); outsider.force_login(fixtures.synthetic_user("synthetic-outsider"))
        self.assertEqual(outsider.get(f"/my-documents/{self.doc.pk}/?lang=fr").status_code, 404)

    def test_output_uses_current_status_inclusive_end_and_stable_verification(self):
        credentials = s.decrypt(self.doc.credentials)
        for day, status in ((self.activity.starts_on-timedelta(days=1), "pending"),
                            (self.activity.ends_on, "active"),
                            (self.activity.ends_on+timedelta(days=1), "expired")):
            with patch("governance.services.today", return_value=day):
                for language in ("ar", "fr", "en"):
                    self.assertIn(vocabulary(language)[1][status], printable(self.doc, language))
                result = s.lookup_document(token=credentials["token"])
                self.assertEqual(result["status"], status)
                self.assertEqual(result["type"], "activity invitation")
                self.assertEqual(set(result), {"full_name", "type", "document_type", "reference", "valid_from", "valid_until", "status"})
        render_outbox(Outbox.objects.get(document=self.doc).pk)
        self.doc.refresh_from_db()
        self.assertIn('lang="ar"', s.decrypt(self.doc.rendered))
        self.registration.state = "cancelled"; self.registration.save(update_fields=["state"])
        self.doc.refresh_from_db()
        for language in ("ar", "fr", "en"):
            response = self.client.get(f"/my-documents/{self.doc.pk}/?lang={language}")
            self.assertContains(response, vocabulary(language)[1]["cancelled"])
        self.assertEqual(s.lookup_document(token=credentials["token"])["status"], "cancelled")
        self.assertEqual(Document.objects.count(), 1)

    def test_replacement_invalidates_old_credentials_without_extending_activity(self):
        old_credentials = s.decrypt(self.doc.credentials)
        result = s.replace_document(self.request, key="synthetic-invitation-replacement",
            document_id=self.doc.pk, reason="Synthetic damaged invitation")
        replacement = Document.objects.get(pk=result["document"])
        self.doc.refresh_from_db()
        self.assertEqual(s.lookup_document(token=old_credentials["token"])["status"], "cancelled")
        self.assertEqual(s.public_document(replacement)["valid_until"], str(self.activity.ends_on))
        self.assertNotEqual(old_credentials, s.decrypt(replacement.credentials))
        for language in ("ar", "fr", "en"):
            self.assertIn(vocabulary(language)[1]["cancelled"], printable(self.doc, language))
            self.assertIn(vocabulary(language)[1]["active"], printable(replacement, language))
        self.assertEqual(Document.objects.count(), 2)
