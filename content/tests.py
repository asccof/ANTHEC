from io import StringIO
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from governance.models import Authority
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase, SimpleTestCase
from wagtail.models import Locale, Page, PageViewRestriction, Site
from content.models import InstitutionalPage
from content.translation import (
    DisabledTranslator,
    FixtureTranslator,
    TranslationUnavailable,
)


class ContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.home = Site.objects.get(is_default_site=True).root_page.specific
        cls.admin = get_user_model().objects.create_superuser(
            "synthetic-admin", "admin@example.invalid", "synthetic-test-password"
        )

        Authority.objects.create(primary=cls.admin)
        cls.device = TOTPDevice.objects.create(user=cls.admin, confirmed=True)

    def admin_login(self, client):
        client.force_login(self.admin)
        session = client.session
        session["otp_device_id"] = self.device.persistent_id
        session["authority_epoch"] = 0
        session["reauth_at"] = timezone.now().timestamp()
        session.save()

    def test_localized_pages_have_actual_localized_content(self):
        expected = {
            "ar": "منصة ANTHEEC التجريبية",
            "fr": "Plateforme de démonstration ANTHEEC",
            "en": "ANTHEEC demonstration platform",
        }
        for code, title in expected.items():
            response = self.client.get(f"/{code}/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, title)
            self.assertContains(response, f'lang="{code}"')
            self.assertContains(response, 'dir="rtl"' if code == "ar" else 'dir="ltr"')

    def test_translations_are_one_logical_group(self):
        self.assertEqual(self.home.get_translations(inclusive=True).count(), 3)
        self.assertEqual(
            set(
                self.home.get_translations(inclusive=True).values_list(
                    "translation_key", flat=True
                )
            ),
            {self.home.translation_key},
        )

    def test_seed_is_idempotent(self):
        count = Page.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Page.objects.count(), count)

    def test_draft_is_not_public(self):
        self.home.add_child(
            instance=InstitutionalPage(
                title="Synthetic draft", slug="draft", live=False
            )
        )
        self.assertEqual(self.client.get("/ar/draft/").status_code, 404)

    def test_saved_draft_does_not_change_live_content(self):
        old_title = self.home.title
        self.home.title = "Unpublished change"
        self.home.save_revision(user=self.admin)
        response = self.client.get("/ar/")
        self.assertContains(response, old_title)
        self.assertNotContains(response, "Unpublished change")

    def test_publish_and_restore_keep_revision_history(self):
        original = self.home.get_latest_revision()
        original_title = self.home.title
        self.home.title = "Published synthetic revision"
        self.home.save_revision(user=self.admin).publish(user=self.admin)
        self.assertContains(self.client.get("/ar/"), "Published synthetic revision")
        before = self.home.revisions.count()
        restored = original.as_object()
        restored.save_revision(user=self.admin).publish(user=self.admin)
        self.assertContains(self.client.get("/ar/"), original_title)
        self.assertEqual(self.home.revisions.count(), before + 1)

    def test_unpublish_removes_page_and_navigation_link(self):
        french = self.home.get_translation(Locale.objects.get(language_code="fr"))
        french.unpublish(user=self.admin)
        self.assertEqual(self.client.get("/fr/").status_code, 404)
        self.assertNotContains(self.client.get("/ar/"), 'hreflang="fr"')

    def test_private_translation_not_in_public_language_switch(self):
        french = self.home.get_translation(Locale.objects.get(language_code="fr"))
        PageViewRestriction.objects.create(
            page=french, restriction_type=PageViewRestriction.LOGIN
        )
        self.assertNotContains(self.client.get("/ar/"), 'hreflang="fr"')

    def test_public_text_is_escaped(self):
        self.home.body = [
            ("heading", '<script>alert("synthetic")</script>'),
            ("paragraph", "<img src=x onerror=alert(1)>"),
        ]
        self.home.save_revision().publish()
        response = self.client.get("/ar/")
        self.assertNotContains(response, "<script>")
        self.assertNotContains(response, "<img src=x")
        self.assertContains(response, "&lt;script&gt;")

    def test_anonymous_admin_access_redirects(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertEqual(
            self.client.get(f"/admin/pages/{self.home.pk}/edit/").status_code, 302
        )

    def test_admin_can_open_block_editor(self):
        self.admin_login(self.client)
        response = self.client.get(f"/admin/pages/{self.home.pk}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "body")

    def test_admin_access_permission_does_not_grant_edit_permission(self):
        user = get_user_model().objects.create_user(
            "synthetic-editor",
            "editor@example.invalid",
            "synthetic-test-password",
            is_staff=True,
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            )
        )
        self.client.force_login(user)
        url = f"/admin/pages/{self.home.pk}/edit/"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(
            self.client.post(
                url, {"title": "Forbidden change", "action-publish": "Publish"}
            ).status_code,
            403,
        )
        self.home.refresh_from_db()
        self.assertNotEqual(self.home.title, "Forbidden change")

    def test_admin_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.admin_login(client)
        response = client.post(
            f"/admin/pages/{self.home.pk}/edit/", {"title": "CSRF attempt"}
        )
        self.assertEqual(response.status_code, 403)

    def test_no_public_document_route(self):
        for url in (
            "/documents/1/secret.pdf",
            "/private-media/secret.pdf",
            "/ar/private-media/secret.pdf",
        ):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_health_does_not_disclose_settings(self):
        response = self.client.get("/health/")
        self.assertEqual(
            response.json(),
            {"project": "ANTHEEC", "mode": "development", "status": "ok"},
        )

    def test_security_headers(self):
        response = self.client.get("/ar/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")


class TranslationBoundaryTests(SimpleTestCase):
    def test_live_translation_is_disabled(self):
        with self.assertRaises(TranslationUnavailable):
            DisabledTranslator().translate(
                text="Synthetic content", source="en", target="ar"
            )

    def test_fixture_translation_is_explicit_and_limited(self):
        provider = FixtureTranslator(
            {("en", "fr", "Synthetic content"): "Contenu synthétique"}
        )
        self.assertEqual(
            provider.translate(text="Synthetic content", source="en", target="fr"),
            "Contenu synthétique",
        )
        with self.assertRaises(TranslationUnavailable):
            provider.translate(text="Unknown", source="en", target="fr")
        with self.assertRaises(ValueError):
            provider.translate(text="Synthetic content", source="en", target="de")
