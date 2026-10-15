"""Synthetic presentation acceptance: scope, current prices and trial restrictions."""
from io import StringIO
from datetime import timedelta
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.utils import timezone
from wagtail.models import Site
from .models import InstitutionalPage
from governance import tests as fixtures
from governance.models import Authority, Price, Person, Application, AccreditationCase
from governance.services import encrypt, year_after
from governance.test_deployment import PRIVATE_MIDDLEWARE

class PresentationTests(TestCase):
    http_login = fixtures.PolicyTests.http_login
    def setUp(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_policy_prices", stdout=StringIO())
        self.home = Site.objects.get(is_default_site=True).root_page.specific
        self.admin = fixtures.synthetic_user("synthetic-presentation-owner", True)
        Authority.objects.create(primary=self.admin)
    def test_localized_sections_identity_and_navigation(self):
        expected = {
            "ar": ("فضاء للانتماء والتطوير المهني", "العضو المؤسس والعضو الشرفي"),
            "fr": ("Un espace d’appartenance", "Membres fondateurs et honoraires"),
            "en": ("A space for belonging", "Founder and honorary members"),
        }
        for language, texts in expected.items():
            response=self.client.get("/"+language+"/")
            self.assertEqual(response.status_code,200)
            for text in texts:self.assertContains(response,text)
            self.assertContains(response,"| ANTHEC</title>")
            for anchor in ("main-content","about","membership","accreditation","privacy"):
                self.assertContains(response,'id="'+anchor+'"')
            self.assertContains(response,'href="/activities/?lang='+language+'"')
            self.assertContains(response,'href="/partners/?lang='+language+'"')
            self.assertContains(response,'lang="'+language+'"')
            self.assertContains(response,'dir="rtl"' if language=="ar" else 'dir="ltr"')
    def test_prices_use_effective_versions_and_exclude_free_designation_overrides(self):
        moment=timezone.now()
        Price.objects.create(tier="affiliate",amount="612.34",starts_at=moment-timedelta(minutes=1))
        Price.objects.create(tier="affiliate",amount="98765.43",starts_at=moment+timedelta(days=2))
        Price.objects.create(tier="honorary",amount="76543.21",starts_at=moment)
        response=self.client.get("/en/")
        self.assertContains(response,"612.34")
        self.assertNotContains(response,"98765.43")
        self.assertNotContains(response,"76543.21")
        self.assertContains(response,"Free permanent designations")
        self.assertEqual(len(response.context["membership_prices"]),4)
        self.assertEqual({row["tier"] for row in response.context["membership_prices"]},{"general","affiliate","advanced","accredited"})
    def test_private_records_and_fees_are_not_public_page_data(self):
        person=Person.objects.create(full_name="PRIVATE-PERSON",contact="private-identity@example.invalid",verification_notice_at=timezone.now())
        Application.objects.create(person=person,tier="affiliate",quote="54321.09",quoted_on=timezone.localdate())
        start=timezone.localdate()
        AccreditationCase.objects.create(kind="institution",subject_name="PRIVATE-INSTITUTION",starts_on=start,ends_on=year_after(start),private_payload=encrypt({"fee":"45678.90","criteria":"PRIVATE-CRITERIA","assessment":"PRIVATE-ASSESSMENT"}))
        response=self.client.get("/en/")
        for secret in ("PRIVATE-PERSON","private-identity@example.invalid","54321.09","PRIVATE-INSTITUTION","45678.90","PRIVATE-CRITERIA","PRIVATE-ASSESSMENT"):
            self.assertNotContains(response,secret)
        self.assertContains(response,"not a government professional licence")
    @override_settings(ANTHEEC_OWNER_TESTING=True,MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_trial_keeps_anonymous_gate_and_disabled_signup_on_owner_preview(self):
        self.assertEqual(self.client.get("/ar/").status_code,404)
        self.http_login()
        for language in ("ar","fr","en"):
            response=self.client.get("/"+language+"/")
            self.assertEqual(response.status_code,200)
            self.assertIn("no-store",response["Cache-Control"])
            self.assertIn("noindex",response["X-Robots-Tag"])
            self.assertContains(response,'aria-disabled="true"')
            self.assertNotContains(response,'href="/members/signup/')
            self.assertTrue(response.context["owner_testing"])
        self.assertEqual(self.client.post("/members/signup/",{}).status_code,404)
    def test_child_pages_keep_editorial_content_without_homepage_sections(self):
        child=self.home.add_child(instance=InstitutionalPage(title="Synthetic Editorial Page",slug="editorial-sample",live=False,body=[("heading","Synthetic heading"),("paragraph","Synthetic editable text")]))
        child.save_revision().publish()
        response=self.client.get("/ar/editorial-sample/")
        self.assertContains(response,"Synthetic Editorial Page")
        self.assertContains(response,"Synthetic editable text")
        self.assertNotContains(response,'id="membership"')
        self.assertFalse(response.context["is_site_home"])
    def test_missing_prices_do_not_invent_fallback_amounts(self):
        Price.objects.filter(tier="affiliate").delete()
        response=self.client.get("/en/")
        self.assertContains(response,"Set by administration")
        affiliate=next(row for row in response.context["membership_prices"] if row["tier"]=="affiliate")
        self.assertIsNone(affiliate["amount"])
