from datetime import timedelta
from io import StringIO, BytesIO
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from bs4 import BeautifulSoup
from PIL import Image
from wagtail.models import Site
from governance.models import Activity, ActivityImage
from governance.test_activity_editorial import content


@override_settings(ANTHEEC_OPERATIONAL=True)
class HomeActivitiesTests(TestCase):
    def setUp(self):
        call_command('seed_demo',stdout=StringIO())
        home=Site.objects.get(is_default_site=True).root_page.specific
        for page in home.get_translations(inclusive=True).specific():
            page.editorial_home=True
            page.save_revision().publish()
        self.today=timezone.localdate()

    def activity(self, day, published=True):
        return Activity.objects.create(title='Synthetic public activity',starts_on=day,
            ends_on=day,capacity=5,is_published=published,consent_text='PRIVATE GUARDIAN TERMS',presentation=content())

    def test_live_upcoming_and_past_posts_images_and_verification_in_all_locales(self):
        future=self.activity(self.today+timedelta(days=1))
        past=self.activity(self.today-timedelta(days=1))
        output=BytesIO();Image.new('RGB',(8,5),'#146e70').save(output,'JPEG')
        photo=ActivityImage.objects.create(activity=future,jpeg=output.getvalue(),caption='Synthetic public caption')
        image_url=reverse('activity_editorial_image',args=[future.pk,photo.serial])
        for lang in ('ar','fr','en'):
            response=self.client.get('/'+lang+'/')
            self.assertEqual(response.status_code,200)
            soup=BeautifulSoup(response.content,'html.parser')
            self.assertEqual(len(soup.select('.home-activity-period')),2)
            self.assertEqual(len(soup.select('.home-activity-card')),2)
            self.assertEqual(len(soup.select('.home-activity-card img')),1)
            self.assertContains(response,image_url)
            self.assertContains(response,f'/activities/{past.pk}/about/?lang={lang}')
            self.assertContains(response,f'/activities/?lang={lang}&amp;period=past')
            self.assertContains(response,f'/verify/?lang={lang}')
            self.assertNotContains(response,'PRIVATE GUARDIAN TERMS')
        self.assertEqual(self.client.get(image_url).status_code,200)

    def test_hidden_posts_and_inactive_photos_never_appear_and_hiding_removes_them(self):
        public=self.activity(self.today)
        hidden=self.activity(self.today+timedelta(days=1),False)
        image=ActivityImage.objects.create(activity=public,jpeg=b'not-loaded-in-listing',active=False,caption='Hidden caption')
        response=self.client.get('/ar/')
        self.assertNotContains(response,f'/activities/{hidden.pk}/about/')
        self.assertNotContains(response,str(image.serial))
        self.assertContains(response,f'/activities/{public.pk}/about/')
        public.is_published=False;public.save()
        response=self.client.get('/ar/')
        self.assertNotContains(response,f'/activities/{public.pk}/about/')
        self.assertContains(response,'home-activity-empty',count=2)

    def test_date_boundary_bounded_order_and_image_payload_deferred(self):
        from governance.activity_public import homepage_activities
        today=self.activity(self.today)
        for offset in (1,2,3,4,-1,-2,-3,-4):self.activity(self.today+timedelta(days=offset))
        groups=homepage_activities('en')
        self.assertEqual([len(g['activities']) for g in groups],[3,3])
        self.assertEqual(groups[0]['activities'][0].pk,today.pk)
        self.assertTrue(all(row.ends_on<self.today for row in groups[1]['activities']))
        photo=ActivityImage.objects.create(activity=today,jpeg=b'private-binary-test')
        groups=homepage_activities('en')
        loaded=groups[0]['activities'][0].public_images[0]
        self.assertEqual(loaded.pk,photo.pk)
        self.assertIn('jpeg',loaded.get_deferred_fields())
