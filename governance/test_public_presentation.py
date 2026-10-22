"""Browser-specific failures stay private while machine verification stays stable."""
from django.test import TestCase, Client
from .models import PartnershipRequest, Partner


class PublicPresentationTests(TestCase):
    def test_anonymous_verification_opens_directly_without_account_credentials(self):
        from bs4 import BeautifulSoup
        for language in ('ar','fr','en'):
            response=self.client.get('/verify/?lang='+language)
            self.assertEqual(response.status_code,200)
            soup=BeautifulSoup(response.content,'html.parser')
            self.assertFalse(soup.select('input[type="password"],input[name="username"],input[name="email"]'))
            self.assertEqual(soup.select_one('#document-reference')['type'],'text')
            self.assertEqual(soup.select_one('#document-code')['type'],'text')
            self.assertTrue(soup.select_one('#document-code-help').get_text(strip=True))
            self.assertContains(response,'requestSubmit()')
            self.assertNotContains(response,'ANTHEEC')

    def test_verification_html_failure_keeps_form_and_does_not_echo_credentials(self):
        for language in ('ar','fr','en'):
            response = self.client.post('/verify/?lang='+language,
                {'serial':'synthetic-secret-reference', 'code':'synthetic-secret-code', 'token':'synthetic-private-token'}, HTTP_ACCEPT='text/html')
            self.assertEqual(response.status_code,404)
            self.assertContains(response,'id="verification"',status_code=404)
            self.assertContains(response,'role="alert"',status_code=404)
            self.assertContains(response,'name="referrer" content="same-origin"',status_code=404)
            self.assertContains(response,f'lang="{language}"',status_code=404)
            for secret in ('synthetic-secret-reference','synthetic-secret-code','synthetic-private-token'):
                self.assertNotContains(response,secret,status_code=404)
            machine = self.client.post('/verify/?lang='+language, {'serial':'synthetic'}, HTTP_ACCEPT='application/json')
            self.assertEqual(machine.status_code,404)
            self.assertEqual(machine.json(),{'error':'Document not found'})

    def test_verification_html_rate_limit_and_csrf_remain_enforced(self):
        for _ in range(30):
            self.client.post('/verify/', {'serial':'synthetic'}, HTTP_ACCEPT='application/json')
        response=self.client.post('/verify/?lang=fr', {'token':'synthetic-private-token'},HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code,429)
        self.assertContains(response,'role="alert"',status_code=429)
        self.assertNotContains(response,'synthetic-private-token',status_code=429)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/verify/',{}).status_code,403)

    def test_partner_pages_use_public_navigation_and_preserve_request_privacy(self):
        row=PartnershipRequest.objects.create(organization='Synthetic institution',contact_email='private@example.invalid',message='PRIVATE-PROPOSAL',notice_acknowledged=True,state='approved')
        Partner.objects.create(request=row,name_ar='Synthetic AR',name_fr='Synthetic FR',name_en='Synthetic EN',summary_ar='Synthetic summary',summary_fr='Synthetic résumé',summary_en='Synthetic overview',public_visible=True,state='active')
        for lang in ('ar','fr','en'):
            response=self.client.get('/partners/?lang='+lang)
            self.assertContains(response,'public-services.css')
            self.assertContains(response,'href="/verify/?lang='+lang+'"')
            self.assertNotContains(response,'private@example.invalid')
            self.assertNotContains(response,'PRIVATE-PROPOSAL')
        from django.urls import reverse
        response=self.client.get(reverse('partnership_request')+'?lang=fr')
        self.assertContains(response,'public-services.css')
        self.assertContains(response,'csrfmiddlewaretoken')
