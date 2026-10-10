from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from wagtail.models import Site
from content.models import InstitutionalPage
from content.translation import DisabledTranslator, TranslationUnavailable

class CMSAcceptanceTests(TestCase):
    def setUp(self):
        call_command('seed_demo', verbosity=0)
        self.home = Site.objects.get(is_default_site=True).root_page.specific

    def test_localized_pages_and_direction(self):
        for code, text in [('ar','منصة ANTHEEC'), ('fr','Plateforme de démonstration'), ('en','ANTHEEC demonstration')]:
            response = self.client.get(f'/{code}/')
            self.assertContains(response, text)
            self.assertContains(response, f'lang="{code}"')
            self.assertContains(response, 'dir="rtl"' if code == 'ar' else 'dir="ltr"')

    def test_unpublished_page_is_not_public(self):
        page = self.home.add_child(instance=InstitutionalPage(title='Synthetic draft', slug='draft',live=False))
        page.save_revision()
        self.assertEqual(self.client.get('/ar/draft/').status_code,404)
        page.save_revision().publish()
        self.assertContains(self.client.get('/ar/draft/'),'Synthetic draft')

    def test_revision_restore(self):
        first=self.home.save_revision()
        self.home.title='New synthetic title'
        self.home.save_revision().publish()
        first.as_object().save_revision().publish()
        self.home.refresh_from_db()
        self.assertNotEqual(self.home.title,'New synthetic title')

    def test_anonymous_admin_denied(self):
        self.assertEqual(self.client.get('/admin/').status_code,302)

    def test_member_admin_denied(self):
        user=get_user_model().objects.create_user(username='synthetic-member',password='test-only')
        self.client.force_login(user)
        self.assertIn(self.client.get('/admin/').status_code,[302,403])

    def test_seed_idempotent(self):
        count=InstitutionalPage.objects.count()
        call_command('seed_demo',verbosity=0)
        self.assertEqual(InstitutionalPage.objects.count(),count)

    def test_provider_disabled(self):
        with self.assertRaises(TranslationUnavailable):
            DisabledTranslator().translate(text='synthetic',source='ar',target='en')

    def test_private_media_not_served(self):
        self.assertEqual(self.client.get('/private-media/synthetic.pdf').status_code,404)


class SeedSafetyTests(TestCase):
    def test_existing_leaf_homepage_is_preserved(self):
        from django.core.management.base import CommandError
        site = Site.objects.get(is_default_site=True)
        original = site.root_page
        original.title = 'Existing synthetic homepage'
        original.save()
        before = InstitutionalPage.objects.count()
        with self.assertRaises(CommandError):
            call_command('seed_demo', verbosity=0)
        site.refresh_from_db()
        self.assertEqual(site.root_page_id, original.pk)
        self.assertEqual(site.root_page.title, 'Existing synthetic homepage')
        self.assertEqual(InstitutionalPage.objects.count(), before)

    def test_modified_placeholder_with_revision_is_preserved(self):
        from django.core.management.base import CommandError
        site = Site.objects.get(is_default_site=True)
        site.root_page.save_revision()
        original_id = site.root_page_id
        with self.assertRaises(CommandError):
            call_command('seed_demo', verbosity=0)
        site.refresh_from_db()
        self.assertEqual(site.root_page_id, original_id)
