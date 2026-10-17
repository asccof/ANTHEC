from io import StringIO
from django.test import TestCase, Client
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.urls import reverse
from wagtail.models import Site
from .models import PublicContact
from .presentation import vocabulary
from governance import tests as fixtures
from governance.models import Authority


class PublicContactTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        call_command("seed_demo", stdout=StringIO())
        self.site = Site.objects.get(is_default_site=True)

    def test_owner_contacts_shared_across_locales_without_writing_on_public_get(self):
        for lang in ("ar", "fr", "en"):
            response = self.client.get("/" + lang + "/")
            self.assertContains(response, 'id="contact"')
            self.assertContains(response, 'href="tel:+212663400190"')
            self.assertContains(response, 'href="https://wa.me/212663400190"')
            self.assertContains(response, vocabulary(lang)["contact_email"])
            self.assertNotContains(response, 'href="mailto:')
        self.assertFalse(PublicContact.objects.exists())

    def test_saved_email_and_localized_addresses_are_escaped_and_update_footer(self):
        row = PublicContact.objects.create(site=self.site, email="association@example.invalid", address_ar="<script>Synthetic address</script>", address_fr="Synthetic French address", address_en="Synthetic English address")
        response = self.client.get("/ar/")
        self.assertContains(response, 'href="mailto:association@example.invalid"')
        self.assertContains(response, "&lt;script&gt;Synthetic address&lt;/script&gt;")
        self.assertNotContains(response, "<script>Synthetic address</script>")
        self.assertContains(self.client.get("/fr/"), "Synthetic French address")
        self.assertContains(self.client.get("/en/"), "Synthetic English address")
        row.phone = "+33600000001"
        row.full_clean()
        row.save()
        response = self.client.get("/en/")
        self.assertContains(response, 'href="https://wa.me/33600000001"')
        self.assertContains(response, 'href="tel:+33600000001"')
        self.assertNotContains(response, "0663400190")

    def test_invalid_links_cannot_be_rendered_even_if_validation_bypassed(self):
        row = PublicContact(site=self.site, phone="javascript:alert(1)", email="a@example.invalid?subject=unsafe")
        with self.assertRaises(ValidationError):
            row.full_clean()
        for bad in ("0663400190\n", "+212663400190\n", "javascript:alert(1)"):
            row.phone = bad
            with self.assertRaises(ValidationError):
                row.full_clean()
        row.save()
        response = self.client.get("/en/")
        self.assertNotContains(response, "javascript:")
        self.assertNotContains(response, "subject=unsafe")
        self.assertNotContains(response, 'href="mailto:')
        self.assertNotContains(response, 'href="tel:')

    def test_admin_edit_requires_authority_mfa_and_csrf(self):
        url = reverse("wagtailsettings:edit", args=("content", "publiccontact", self.site.pk))
        self.assertEqual(self.client.get(url).status_code, 302)
        staff = fixtures.synthetic_user("synthetic-contact-staff", True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        admin = fixtures.synthetic_user("synthetic-director", True)
        Authority.objects.create(primary=admin)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(admin)
        self.assertEqual(browser.get(url).status_code, 302)
        self.http_login(client=browser, user=admin)
        response = browser.get(url)
        self.assertEqual(response.status_code, 200)
        values = dict(phone="+212600000001", address_ar="Synthetic AR", address_fr="Synthetic FR", address_en="Synthetic EN", email="contact@example.invalid")
        self.assertEqual(browser.post(url, values).status_code, 403)
        values["csrfmiddlewaretoken"] = browser.cookies["csrftoken"].value
        self.assertEqual(browser.post(url, values).status_code, 302)
        row = PublicContact.objects.get(site=self.site)
        self.assertEqual(row.email, "contact@example.invalid")
        self.assertContains(self.client.get("/en/"), 'href="mailto:contact@example.invalid"')
