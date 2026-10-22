from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from bs4 import BeautifulSoup
from wagtail.models import Site
from .models import InstitutionalPage, PublicLeader, MultilingualPublication
from .wagtail_hooks import LeadershipPermissionPolicy
from governance import tests as fixtures
from governance.models import Authority, Person


@override_settings(ANTHEEC_OPERATIONAL=True)
class MultilingualTests(TestCase):
    def setUp(self):
        call_command('seed_demo', stdout=StringIO())
        call_command('publish_approved_editorial', apply=True, stdout=StringIO())
        self.site = Site.objects.get(is_default_site=True)
        self.home = self.site.root_page.specific

    def apply(self):
        call_command('publish_multilingual_editorial', apply=True, stdout=StringIO())

    def test_plan_and_mode_gate_are_read_only(self):
        before = InstitutionalPage.objects.count()
        call_command('publish_multilingual_editorial', stdout=StringIO())
        self.assertEqual(InstitutionalPage.objects.count(), before)
        self.assertFalse(PublicLeader.objects.exists())
        with override_settings(ANTHEEC_OPERATIONAL=False), self.assertRaises(CommandError):self.apply()
        self.assertFalse(MultilingualPublication.objects.exists())

    def test_linked_pages_names_and_compact_navigation_in_all_languages(self):
        self.apply()
        self.assertEqual(PublicLeader.objects.count(),7)
        self.assertEqual(Person.objects.count(),0)
        for code in ('ar','fr','en'):
            response=self.client.get('/'+code+'/')
            self.assertEqual(response.status_code,200)
            soup=BeautifulSoup(response.content,'html.parser')
            self.assertEqual(len(soup.select('.founders-grid article')),7)
            self.assertEqual(len(soup.select('.office-card')),2)
            self.assertFalse(soup.select('.editorial-navigation'))
            self.assertEqual(len(soup.select('.main-nav details')),4)
            self.assertEqual(len(soup.select('.hero-actions a')),2)
            self.assertContains(response,'إدريس هلالي' if code=='ar' else 'Driss Helali')
            for source in self.home.get_children():
                page=source if code=='ar' else source.get_translation(self.home.get_translations().get(locale__language_code=code).locale)
                response=self.client.get('/'+code+'/'+page.slug+'/')
                self.assertEqual(response.status_code,200)
                self.assertContains(response,page.title)
                self.assertEqual(page.get_translations(inclusive=True).count(),3)
                if code!='ar':self.assertNotContains(response,'مرحلة التطوير')
            self.assertContains(self.client.get('/'+code+'/governance/'),'فؤاد العلوي العماري' if code=='ar' else 'Fouad El Alaoui El Omari')

    def test_redeploy_preserves_edits_deletions_and_unpublication(self):
        self.apply()
        leader=PublicLeader.objects.first()
        leader.name_ar='اسم معدل';leader.name_latin='Edited public name';leader.save()
        PublicLeader.objects.filter(role='founder').last().delete()
        local=self.home.get_translations().get(locale__language_code='fr').specific
        local.body=[('heading','Titre modifié'),('paragraph','Texte modifié')];local.save_revision().publish()
        child=local.get_children().get(slug='about').specific;child.unpublish()
        self.apply()
        self.assertEqual(PublicLeader.objects.count(),6)
        self.assertEqual(PublicLeader.objects.get(pk=leader.pk).name_latin,'Edited public name')
        local.refresh_from_db();self.assertEqual(local.body[0].value,'Titre modifié')
        response=self.client.get('/fr/')
        self.assertContains(response,'Edited public name');self.assertNotContains(response,'href="/fr/about/"')
        self.assertEqual(self.client.get('/fr/about/').status_code,404)
        leader.published=False;leader.save()
        for code in ('ar','fr','en'):
            response=self.client.get('/'+code+'/governance/')
            self.assertNotContains(response,leader.name_ar);self.assertNotContains(response,leader.name_latin)

    def test_slug_conflict_rolls_back_all_languages(self):
        local=self.home.get_translations().get(locale__language_code='en').specific
        local.add_child(instance=InstitutionalPage(title='Existing owner page',slug='about',locale=local.locale,live=False))
        with self.assertRaises(CommandError):self.apply()
        self.assertFalse(PublicLeader.objects.exists());self.assertFalse(MultilingualPublication.objects.exists())
        self.assertEqual(self.home.get_translations().get(locale__language_code='fr').get_children().count(),0)

    def test_draft_and_changed_receipt_are_not_overwritten(self):
        local=self.home.get_translations().get(locale__language_code='fr').specific
        local.body=[('paragraph','Draft owner work')];local.save_revision()
        with self.assertRaisesMessage(CommandError,'Unpublished'):self.apply()
        self.assertFalse(PublicLeader.objects.exists())

    def test_unique_office_and_primary_only_permissions(self):
        self.apply()
        duplicate=PublicLeader(site=self.site,name_ar='اسم اصطناعي',name_latin='Synthetic office',role='president',published=True)
        with self.assertRaises(ValidationError):duplicate.full_clean()
        policy=LeadershipPermissionPolicy(PublicLeader)
        ordinary=fixtures.synthetic_user('synthetic-directory-staff',True)
        owner=fixtures.synthetic_user('synthetic-directory-owner',True)
        Authority.objects.create(primary=owner)
        self.assertFalse(policy.user_has_permission(ordinary,'change'));self.assertTrue(policy.user_has_permission(owner,'change'))
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(policy.user_has_permission(AnonymousUser(),'view'))

    def test_primary_admin_can_edit_directory_through_real_form(self):
        from django.urls import reverse
        self.apply()
        owner=fixtures.synthetic_user('synthetic-directory-form-owner',True)
        Authority.objects.create(primary=owner)
        fixtures.PolicyTests.http_login(self,user=owner)
        leader=PublicLeader.objects.first()
        index=reverse('wagtailsnippets_content_publicleader:list')
        response=self.client.get(index)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,leader.name_ar)
        edit=reverse('wagtailsnippets_content_publicleader:edit',args=[leader.pk])
        response=self.client.get(edit)
        self.assertEqual(response.status_code,200)
        response=self.client.post(edit,{'site':self.site.pk,'name_ar':'اسم معدل','name_latin':'Edited directory name',
            'role':'president','founder':'on','published':'on','sort_order':0})
        self.assertEqual(response.status_code,302)
        leader.refresh_from_db();self.assertEqual(leader.name_latin,'Edited directory name')
        self.assertContains(self.client.get('/en/governance/'),'Edited directory name')
        MultilingualPublication.objects.update(digest='0'*64)
        with self.assertRaisesMessage(CommandError,'edition changed'):self.apply()

    def test_hiding_entire_directory_does_not_expose_legacy_blocks(self):
        self.apply()
        self.home.body=[('heading','Public heading'),('paragraph','Public introduction'),
            ('leadership',{'role':'president','name':'Legacy synthetic name'})]
        self.home.save_revision().publish()
        PublicLeader.objects.update(published=False)
        response=self.client.get('/ar/')
        self.assertNotContains(response,'Legacy synthetic name')
        self.assertNotContains(response,'إدريس هلالي')

    def test_restricted_source_blocks_new_translation_publication(self):
        from wagtail.models import PageViewRestriction
        source=self.home.get_children().get(slug='about')
        PageViewRestriction.objects.create(page=source,restriction_type='login')
        with self.assertRaisesMessage(CommandError,'restricted'):self.apply()
        self.assertFalse(MultilingualPublication.objects.exists())
        self.assertFalse(PublicLeader.objects.exists())
