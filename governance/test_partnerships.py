import uuid
from io import StringIO
from django.test import TestCase, Client, override_settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command, CommandError
from .tests import synthetic_user, administrative_request
from . import tests as policy_fixtures
from . import partner_services as service
from .test_deployment import PRIVATE_MIDDLEWARE
from .models import Authority, PartnershipRequest, Partner, Audit, Document, Payment

class PartnershipTests(TestCase):
    http_login=policy_fixtures.PolicyTests.http_login
    def setUp(self):
        self.admin=synthetic_user('synthetic-partner-owner',True)
        Authority.objects.create(primary=self.admin)
        self.holder=synthetic_user('synthetic-partner-member')
        self.request=administrative_request(self.admin)
        self.row=PartnershipRequest.objects.create(organization='Synthetic Organization',contact_email='private@example.invalid',message='PRIVATE-PROPOSAL',notice_acknowledged=True)
    def decide(self,decision='approved',key=None):
        return service.decide(self.request,key=key or str(uuid.uuid4()),request_id=self.row.pk,decision=decision,reason='PRIVATE-DECISION')
    def update(self,partner_id,**overrides):
        payload={'state':'active','public_visible':True,'reason':'PRIVATE-REASON','name_ar':'شريك اصطناعي','name_fr':'Partenaire fictif','name_en':'Synthetic Partner','summary_ar':'وصف اصطناعي','summary_fr':'Description fictive','summary_en':'Synthetic description','website':'https://organization.example.invalid'}
        payload.update(overrides)
        return service.update(self.request,key=str(uuid.uuid4()),partner_id=partner_id,**payload)
    def test_review_idempotency_and_public_allowlist_and_state(self):
        key=str(uuid.uuid4()); result=self.decide(key=key)
        self.assertEqual(self.decide(key=key),result)
        self.assertEqual(Partner.objects.count(),1)
        pk=result['partner']
        self.assertNotContains(self.client.get('/partners/?lang=en'),'Synthetic Organization')
        self.update(pk)
        for lang,name in [('ar','شريك اصطناعي'),('fr','Partenaire fictif'),('en','Synthetic Partner')]:
            response=self.client.get('/partners/?lang='+lang)
            self.assertContains(response,name)
            for private in ['private@example.invalid','PRIVATE-PROPOSAL','PRIVATE-DECISION','PRIVATE-REASON']:
                self.assertNotContains(response,private)
        self.update(pk,state='suspended')
        self.assertNotContains(self.client.get('/partners/?lang=en'),'Synthetic Partner')
        self.assertFalse(Partner.objects.get(pk=pk).public_visible)
        self.update(pk,state='active',public_visible=False)
        self.assertNotContains(self.client.get('/partners/?lang=en'),'Synthetic Partner')
        self.update(pk,state='cancelled')
        self.assertEqual(Document.objects.count(),0); self.assertEqual(Payment.objects.count(),0)
    def test_rejected_and_unnoticed_request_cannot_create_partner(self):
        self.decide('rejected'); self.assertEqual(Partner.objects.count(),0)
        with self.assertRaises(ValidationError): self.decide()
        self.row.state='submitted'; self.row.notice_acknowledged=False; self.row.save()
        with self.assertRaises(ValidationError): self.decide()
        self.assertEqual(Partner.objects.count(),0)
    def test_invalid_url_and_payload_roll_back(self):
        pk=self.decide()['partner']
        for website in ['javascript:alert(1)','http://organization.example.invalid','ftp://organization.example.invalid']:
            with self.assertRaises(ValidationError): self.update(pk,website=website)
        self.assertEqual(Partner.objects.get(pk=pk).website,'')
    @override_settings(ANTHEEC_OWNER_TESTING=True, MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_private_mode_allows_review_but_blocks_submission_and_publication(self):
        self.http_login()
        self.assertEqual(self.client.get('/operations/partners/').status_code,200)
        response=self.client.get('/partners/request/?lang=fr')
        self.assertContains(response,'fieldset disabled')
        self.assertEqual(self.client.post('/partners/request/',{'organization':'Synthetic','contact_email':'test@example.invalid','message':'Synthetic','notice_acknowledged':True}).status_code,403)
        pk=self.decide()['partner']
        with self.assertRaises(PermissionDenied): self.update(pk)
        self.update(pk,public_visible=False)
        self.assertFalse(Partner.objects.get(pk=pk).public_visible)
        client=Client()
        self.assertEqual(client.get('/partners/').status_code,404)
        self.assertEqual(client.get('/operations/partners/').status_code,404)
    def test_mfa_authorization_and_admin_localized_views(self):
        self.client.force_login(self.holder)
        self.assertEqual(self.client.get('/operations/partners/').status_code,403)
        self.http_login()
        for lang in ('ar','fr','en'):
            self.assertEqual(self.client.get('/operations/partners/?lang='+lang).status_code,200)
            self.assertEqual(self.client.get(f'/operations/partners/requests/{self.row.pk}/?lang='+lang).status_code,200)
        self.request.session['reauth_at']=0
        with self.assertRaises(PermissionDenied): self.decide()
    def test_public_request_consent_csrf_throttle_and_no_forwarding_trust(self):
        client=Client(enforce_csrf_checks=True)
        response=client.get('/partners/request/')
        token=client.cookies['csrftoken'].value
        data={'organization':'Synthetic','contact_email':'contact@example.invalid','message':'Synthetic','notice_acknowledged':True,'csrfmiddlewaretoken':token}
        self.assertEqual(client.post('/partners/request/',{}).status_code,403)
        for n in range(5):
            response=client.post('/partners/request/',data,HTTP_X_FORWARDED_FOR=f'192.0.2.{n}')
            self.assertEqual(response.status_code,302)
        self.assertEqual(client.post('/partners/request/',data,HTTP_X_FORWARDED_FOR='192.0.2.100').status_code,429)
        self.assertEqual(PartnershipRequest.objects.count(),6)
        self.assertEqual(Partner.objects.count(),0)
    @override_settings(ANTHEEC_OWNER_TESTING=True)
    def test_fixture_idempotent_and_preserves_review(self):
        call_command('seed_partner_demo',stdout=StringIO())
        call_command('seed_partner_demo',stdout=StringIO())
        self.assertEqual(PartnershipRequest.objects.filter(fixture_key__isnull=False).count(),3)
        self.assertEqual(Audit.objects.filter(action='testing.partnership.created').count(),3)
        self.assertEqual(Partner.objects.count(),0)
    def test_fixture_refuses_non_owner_mode(self):
        with self.assertRaises(CommandError): call_command('seed_partner_demo',stdout=StringIO())

    def test_real_csrf_admin_review_and_hidden_record_edit(self):
        self.client=Client(enforce_csrf_checks=True)
        self.http_login()
        url=f'/operations/partners/requests/{self.row.pk}/?lang=fr'
        self.assertEqual(self.client.post(url,{}).status_code,403)
        response=self.client.get(url)
        token=self.client.cookies['csrftoken'].value
        response=self.client.post(url,{'key':str(uuid.uuid4()),'decision':'approved','reason':'Synthetic review','csrfmiddlewaretoken':token})
        self.assertEqual(response.status_code,302)
        partner=Partner.objects.get(request=self.row)
        self.assertFalse(partner.public_visible)
        detail=f'/operations/partners/{partner.pk}/?lang=fr'
        self.assertEqual(self.client.get(detail).status_code,200)
        data={'key':str(uuid.uuid4()),'name_ar':'اصطناعي','name_fr':'Fictif','name_en':'Synthetic','summary_ar':'','summary_fr':'','summary_en':'','website':'','state':'suspended','reason':'Synthetic suspension','csrfmiddlewaretoken':token}
        self.assertEqual(self.client.post(detail,data).status_code,302)
        partner.refresh_from_db()
        self.assertEqual(partner.state,'suspended')
        self.assertFalse(partner.public_visible)
        self.assertEqual(Audit.objects.filter(action='partner.updated').count(),1)
