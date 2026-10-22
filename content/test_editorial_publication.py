from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from wagtail.models import Site
from content.models import EditorialPublication, InstitutionalPage

@override_settings(ANTHEEC_OPERATIONAL=True)
class EditorialPublicationTests(TestCase):
    def setUp(self):
        call_command('seed_demo', stdout=StringIO())
        self.site = Site.objects.get(is_default_site=True)
        self.home = self.site.root_page.specific

    def apply(self):
        call_command('publish_approved_editorial', apply=True, stdout=StringIO())

    def test_plan_is_read_only_and_nonoperational_apply_refused(self):
        count = InstitutionalPage.objects.count()
        call_command('publish_approved_editorial', stdout=StringIO())
        self.assertEqual(InstitutionalPage.objects.count(), count)
        self.assertFalse(EditorialPublication.objects.exists())
        with override_settings(ANTHEEC_OPERATIONAL=False), self.assertRaises(CommandError):
            self.apply()
        self.assertEqual(InstitutionalPage.objects.count(), count)

    def test_publish_preserves_other_locales_leadership_and_revisions(self):
        translations = list(self.home.get_translations().values('pk','title','live'))
        self.home.body = [('heading','Synthetic heading'),('leadership',{'role':'president','name':'Synthetic President'})]
        self.home.save_revision().publish()
        old_revision = self.home.live_revision_id
        self.apply()
        self.home.refresh_from_db()
        self.assertTrue(self.home.editorial_home)
        self.assertEqual(self.home.get_children().live().count(),16)
        self.assertEqual(list(self.home.get_translations().values('pk','title','live')),translations)
        self.assertTrue(self.home.revisions.filter(pk=old_revision).exists())
        self.assertEqual([b.value['name'] for b in self.home.body if b.block_type=='leadership'],['Synthetic President'])
        self.assertEqual(EditorialPublication.objects.count(),1)
        response=self.client.get('/ar/')
        self.assertContains(response,'معرفةٌ تتطور.')
        self.assertNotContains(response,'مرحلة التطوير')
        self.assertContains(response,'/ar/about/')
        self.assertContains(response,'Synthetic President')
        for child in self.home.get_children():
            response=self.client.get('/ar/'+child.slug+'/')
            self.assertEqual(response.status_code,200)
            self.assertContains(response,child.title)

    def test_redeploy_never_overwrites_later_cms_edits_or_republishes(self):
        self.apply()
        self.home.refresh_from_db()
        self.home.body=[('heading','Owner edited heading'),('paragraph','Owner edited introduction')]
        self.home.save_revision().publish()
        about=self.home.get_children().get(slug='about').specific
        about.unpublish()
        self.apply()
        self.home.refresh_from_db();about.refresh_from_db()
        self.assertEqual(self.home.body[0].value,'Owner edited heading')
        self.assertFalse(about.live)
        self.assertEqual(self.home.get_children().count(),16)
        response=self.client.get('/ar/')
        self.assertContains(response,'Owner edited heading')
        self.assertNotContains(response,'href="/ar/about/"')
        self.assertEqual(self.client.get('/ar/about/').status_code,404)

    def test_existing_slug_and_unpublished_home_changes_block_import(self):
        self.home.add_child(instance=InstitutionalPage(title='Existing content',slug='about',locale=self.home.locale,live=False))
        with self.assertRaises(CommandError):self.apply()
        self.assertFalse(EditorialPublication.objects.exists())
        self.home.refresh_from_db()
        self.assertFalse(self.home.editorial_home)
        self.assertEqual(self.home.get_children().count(),1)
        self.home.body=[('paragraph','Unpublished owner changes')]
        self.home.save_revision()
        with self.assertRaisesMessage(CommandError,'Unpublished homepage'):self.apply()

    def test_private_or_hidden_child_not_listed_in_navigation(self):
        from wagtail.models import PageViewRestriction
        self.apply()
        self.home.refresh_from_db()
        about=self.home.get_children().get(slug='about').specific
        PageViewRestriction.objects.create(page=about,restriction_type='login')
        faq=self.home.get_children().get(slug='faq').specific
        faq.show_in_menus=False;faq.save_revision().publish()
        response=self.client.get('/ar/')
        self.assertNotContains(response,'href="/ar/about/"')
        self.assertNotContains(response,'href="/ar/faq/"')
