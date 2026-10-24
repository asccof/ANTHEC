"""Public tools and private requests; synthetic contacts only."""
import base64
import uuid
from io import BytesIO
from unittest.mock import patch
from bs4 import BeautifulSoup
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Authority, MemberTool, ToolRequest, Audit
from .tests import synthetic_user, administrative_request
from . import tests as policy_fixtures
from . import tool_services
from .privacy_notice import VERSION


class ToolsTests(TestCase):
    http_login = policy_fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user('synthetic-tool-owner', True)
        Authority.objects.create(primary=self.admin)
        self.holder = synthetic_user('synthetic-tool-member')
        self.row = MemberTool.objects.create(title_ar='أداة اصطناعية', title_fr='Outil fictif',
            title_en='Synthetic Tool', description_ar='تفاصيل اصطناعية', description_en='Synthetic details', published=True)
        self.request = administrative_request(self.admin)

    def payload(self, lang='en'):
        response = self.client.get(f'/tools/{self.row.pk}/request/?lang={lang}')
        token = BeautifulSoup(response.content,'html.parser').select_one('[name=token]')['value']
        return dict(token=token, full_name='Synthetic Applicant', phone='+212600000001',
                    email='tool-private@example.invalid')

    def fields(self, **changes):
        data = {field:getattr(self.row,field) for field in
                [key+'_'+lang for lang in ('ar','fr','en') for key in ('title','summary','description')]
                + ['website','sort_order','published']}
        data.update(changes)
        return data

    def test_public_catalog_detail_fallback_escaping_and_hidden_routes(self):
        for lang, title in [('ar','أداة اصطناعية'),('fr','Outil fictif'),('en','Synthetic Tool')]:
            self.assertContains(self.client.get('/tools/?lang='+lang),title)
            self.assertContains(self.client.get(f'/tools/{self.row.pk}/?lang='+lang),title)
        self.row.summary_en='<script>alert(1)</script>'
        self.row.save()
        self.assertContains(self.client.get('/tools/?lang=en'),'&lt;script&gt;')
        self.assertNotContains(self.client.get('/tools/?lang=en'),'<script>alert(1)</script>')
        self.row.website='javascript:alert(1)';self.row.save()
        self.assertNotContains(self.client.get(f'/tools/{self.row.pk}/'),'href="javascript:')
        self.row.published=False;self.row.save()
        for path in (f'/tools/{self.row.pk}/',f'/tools/{self.row.pk}/request/',
                     f'/tools/{self.row.pk}/image/{self.row.image_serial}/'):
            self.assertEqual(self.client.get(path).status_code,404)
        self.assertNotContains(self.client.get('/tools/?lang=en'),'Synthetic Tool')

    @override_settings(ANTHEEC_PRIVACY_NOTICE_ENABLED=True, ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON='2026-10-22')
    def test_request_acknowledgement_idempotency_and_no_public_contacts(self):
        data=self.payload()
        data.update(privacy_acceptance='on',privacy_version=VERSION,privacy_language='en')
        url=f'/tools/{self.row.pk}/request/?lang=en'
        missing=dict(data);missing.pop('privacy_acceptance')
        self.assertEqual(self.client.post(url,missing).status_code,400)
        self.assertEqual(ToolRequest.objects.count(),0)
        response=self.client.post(url,data,follow=True)
        self.assertContains(response,'Your request has been received')
        self.assertEqual(ToolRequest.objects.get().tool_title,'Synthetic Tool')
        self.assertEqual(ToolRequest.objects.get().state,'submitted')
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(ToolRequest.objects.count(),1)
        self.assertEqual(Audit.objects.filter(action='privacy.acknowledged').count(),1)
        for path in ('/tools/?lang=en',f'/tools/{self.row.pk}/?lang=en',url):
            self.assertNotContains(self.client.get(path),'tool-private@example.invalid')
        self.assertNotIn('tool-private@example.invalid',str(list(Audit.objects.values('details','reason'))))

    def test_invalid_contact_csrf_token_cross_tool_and_throttle(self):
        data=self.payload()
        url=f'/tools/{self.row.pk}/request/?lang=en'
        for changes in ({'phone':'bad'},{'email':'bad'},{'full_name':' '},{'token':'invalid'}):
            self.assertEqual(self.client.post(url,{**data,**changes}).status_code,400)
        other=MemberTool.objects.create(title_ar='أخرى',published=True)
        self.assertEqual(self.client.post(f'/tools/{other.pk}/request/',data).status_code,400)
        self.assertEqual(ToolRequest.objects.count(),0)
        self.assertEqual(self.client.post(url,data).status_code,429)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url,data).status_code,403)

    def test_kill_switch_and_unpublication_stop_submissions(self):
        data=self.payload();url=f'/tools/{self.row.pk}/request/'
        with override_settings(ANTHEEC_APPLICATIONS_ENABLED=False):
            self.assertEqual(self.client.post(url,data).status_code,403)
            self.assertNotContains(self.client.get(f'/tools/{self.row.pk}/'),'>Request this tool</a>')
        self.row.published=False;self.row.save()
        self.assertEqual(self.client.post(url,data).status_code,404)
        self.assertEqual(ToolRequest.objects.count(),0)

    def test_admin_authority_editor_image_and_request_review(self):
        self.client.force_login(self.holder)
        self.assertEqual(self.client.get('/operations/tools/').status_code,403)
        self.http_login()
        for lang in ('ar','fr','en'):
            self.assertEqual(self.client.get('/operations/tools/?lang='+lang).status_code,200)
            self.assertEqual(self.client.get('/operations/tools/new/?lang='+lang).status_code,200)
        image=BytesIO();Image.new('RGB',(600,400),'navy').save(image,'PNG')
        response=self.client.post('/operations/tools/new/?lang=en',{
            **self.fields(title_ar='أداة جديدة'), 'key':str(uuid.uuid4()),
            'image_file':SimpleUploadedFile('synthetic.png',image.getvalue(),content_type='image/png')})
        self.assertEqual(response.status_code,302)
        created=MemberTool.objects.exclude(pk=self.row.pk).get()
        self.assertEqual(bytes(created.image)[:2],b'\xff\xd8')
        image_url=f'/tools/{created.pk}/image/{created.image_serial}/'
        self.assertEqual(Client().get(image_url).status_code,200)
        saved=ToolRequest.objects.create(tool=self.row,tool_title='Original tool title',
            full_name='Synthetic Requester',phone='+212600000001',email='private@example.invalid',
            language='en',submission_key=uuid.uuid4())
        response=self.client.get(f'/operations/tools/requests/{saved.pk}/?lang=en')
        self.assertContains(response,'private@example.invalid')
        self.assertEqual(self.client.post(f'/operations/tools/requests/{saved.pk}/',{
            'key':str(uuid.uuid4()),'state':'contacted','notes':'PRIVATE-NOTE'}).status_code,302)
        saved.refresh_from_db();self.assertEqual(saved.state,'contacted')
        self.assertNotContains(Client().get('/tools/'),'PRIVATE-NOTE')
        fields=self.fields(published=False)
        tool_services.save_tool(self.request,key=str(uuid.uuid4()),tool_pk=created.pk,fields=fields)
        self.assertEqual(Client().get(image_url).status_code,404)
        self.assertEqual(self.client.get(f'/operations/tools/{created.pk}/image/{created.image_serial}/').status_code,200)
        self.assertEqual(ToolRequest.objects.count(),1)
        self.request.session['authority_epoch']=-1
        with self.assertRaises(PermissionDenied):
            tool_services.save_tool(self.request,key=str(uuid.uuid4()),tool_pk=self.row.pk,fields=self.fields())

    def test_unsafe_links_and_nonimages_rejected_and_commands_replay(self):
        for link in ('javascript:alert(1)','http://example.invalid','https://user:password@example.invalid'):
            with self.assertRaises(ValidationError):
                tool_services.save_tool(self.request,key=str(uuid.uuid4()),tool_pk=self.row.pk,fields=self.fields(website=link))
        key=str(uuid.uuid4())
        first=tool_services.save_tool(self.request,key=key,tool_pk=self.row.pk,fields=self.fields())
        self.assertEqual(tool_services.save_tool(self.request,key=key,tool_pk=self.row.pk,fields=self.fields()),first)
        self.http_login()
        self.assertEqual(self.client.post('/operations/tools/new/',{
            **self.fields(),'key':str(uuid.uuid4()),'image_file':SimpleUploadedFile('bad.png',b'bad')}).status_code,400)
