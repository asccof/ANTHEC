"""Synthetic operational preparation, no hosted activation or compliance inference."""
import json
from io import StringIO
from unittest.mock import patch
from django.conf import settings
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase, TransactionTestCase, SimpleTestCase, Client, override_settings
from django.test.utils import CaptureQueriesContext
from django_otp.plugins.otp_totp.models import TOTPDevice
from . import test_deployment as deployment_tests
from .models import Authority, RecoveryCode, Audit, RateBucket, Person
from .tests import synthetic_user
from . import tests as fixtures
from .deployment import require_applications_enabled, require_issuance_enabled, require_payments_enabled

MIDDLEWARE = list(settings.MIDDLEWARE)
MIDDLEWARE.insert(MIDDLEWARE.index('governance.middleware.AdminSecurityMiddleware'),
                  'governance.deployment.OperationalMiddleware')


class OperationalSettingsTests(SimpleTestCase):
    settings_process = deployment_tests.PrivateSettingsTests.settings_process

    def config(self, **extra):
        values = {'ANTHEEC_MODE':'operational', 'ANTHEEC_OPERATIONAL_RELEASE_APPROVED':'1',
                  'ANTHEEC_PUBLIC_CONTENT_APPROVED':'1'}
        values.update(extra)
        return self.settings_process(values, command='from django.conf import settings as s; '
            'assert s.ANTHEEC_OPERATIONAL and not s.ANTHEEC_OWNER_TESTING and not s.ANTHEEC_PUBLIC_PREVIEW; '
            'assert not s.DEBUG and s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; '
            'assert "governance.deployment.OperationalMiddleware" in s.MIDDLEWARE; '
            'assert "governance.middleware.AdminSecurityMiddleware" in s.MIDDLEWARE; '
            'assert s.EMAIL_BACKEND.endswith("dummy.EmailBackend")')

    def test_activation_needs_both_distinct_acknowledgements(self):
        self.assertEqual(self.config().returncode, 0)
        for field in ('ANTHEEC_OPERATIONAL_RELEASE_APPROVED','ANTHEEC_PUBLIC_CONTENT_APPROVED'):
            for value in (None, '', '0', 'true', 'yes'):
                with self.subTest(field=field,value=value):
                    self.assertNotEqual(self.config(**{field:value}).returncode,0)

    def test_feature_switches_are_independent_strict_and_off_by_default(self):
        base = {'ANTHEEC_MODE':'operational','ANTHEEC_OPERATIONAL_RELEASE_APPROVED':'1',
                'ANTHEEC_PUBLIC_CONTENT_APPROVED':'1'}
        for active in ('APPLICATIONS','PAYMENTS','ISSUANCE'):
            values = {**base, 'ANTHEEC_'+active+'_ENABLED':'1'}
            result = self.settings_process(values, command='from django.conf import settings as s; '
                f'assert s.ANTHEEC_{active}_ENABLED; '+ '; '.join(
                    f'assert not s.ANTHEEC_{other}_ENABLED' for other in ('APPLICATIONS','PAYMENTS','ISSUANCE') if other!=active))
            self.assertEqual(result.returncode,0,result.stderr)
        for key in ('APPLICATIONS','PAYMENTS','ISSUANCE'):
            for value in ('true','','2','yes'):
                self.assertNotEqual(self.config(**{'ANTHEEC_'+key+'_ENABLED':value}).returncode,0)
        for module in ('dev','build'):
            self.assertNotEqual(self.config(DJANGO_SETTINGS_MODULE='antheec_app.settings.'+module).returncode,0)


@override_settings(ANTHEEC_OPERATIONAL=True, ANTHEEC_OWNER_TESTING=False,
                   ANTHEEC_PUBLIC_PREVIEW=False, MIDDLEWARE=MIDDLEWARE)
class OperationalBoundaryTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        call_command('seed_demo',stdout=StringIO())
        self.admin=synthetic_user('synthetic-release-primary',True)
        Authority.objects.create(primary=self.admin)

    def test_public_and_member_entrypoints_work_but_private_data_remains_protected(self):
        for url in ('/ar/','/fr/','/en/','/activities/','/partners/','/members/login/','/members/signup/','/verify/'):
            with self.subTest(url=url):
                response=self.client.get(url)
                self.assertEqual(response.status_code,200)
                self.assertIn('no-store',response['Cache-Control'])
                for marker in ('class="synthetic-notice', 'class="member-demo', 'class="shell activity-notice'):
                    self.assertNotContains(response,marker)
        self.assertEqual(self.client.get('/my-documents/99999/').status_code,302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').url,'/security/challenge/')
        self.http_login()
        self.assertEqual(self.client.get('/admin/').status_code,200)

    def test_primary_password_only_is_anonymous_on_public_pages_and_blocked_on_private_routes(self):
        from wagtail.models import Site, PageViewRestriction
        from content.models import InstitutionalPage
        home=Site.objects.get(is_default_site=True).root_page.specific
        child=home.add_child(instance=InstitutionalPage(title='PRIVATE CMS',slug='restricted',live=False,
            body=[('paragraph','PRIVATE BODY BEFORE FACTOR')]))
        child.save_revision().publish()
        PageViewRestriction.objects.create(page=child,restriction_type='login')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/ar/').status_code,200)
        response=self.client.get('/ar/restricted/')
        self.assertNotIn(b'PRIVATE BODY BEFORE FACTOR',response.content)
        for url in ('/members/','/members/documents/','/my-documents/999/','/operations/membership/'):
            response=self.client.get(url)
            self.assertEqual(response.url,'/security/challenge/')
        self.assertEqual(self.client.get('/security/challenge/').status_code,200)
        self.assertEqual(self.client.get('/health/').status_code,200)
        self.http_login()
        self.assertEqual(self.client.get('/ar/restricted/').status_code,200)

    @override_settings(ANTHEEC_APPLICATIONS_ENABLED=False, ANTHEEC_PAYMENTS_ENABLED=False,
                       ANTHEEC_ISSUANCE_ENABLED=False)
    def test_kill_switches_block_signup_and_domain_writes(self):
        self.assertEqual(self.client.get('/members/signup/').status_code,403)
        from django.core.exceptions import PermissionDenied
        for guard in (require_applications_enabled, require_payments_enabled, require_issuance_enabled):
            with self.assertRaises(PermissionDenied):guard()

    def test_csrf_rejections_do_not_consume_admin_login_budget(self):
        client=Client(enforce_csrf_checks=True)
        response=client.post('/admin/login/',{'username':'synthetic','password':'invalid'})
        self.assertEqual(response.status_code,403)
        self.assertFalse(RateBucket.objects.exists())
        client.get('/admin/login/')
        token=client.cookies[settings.CSRF_COOKIE_NAME].value
        from .services import digest
        from django.utils import timezone
        key=digest(f'private-login-global:{int(timezone.now().timestamp()//300)}')
        RateBucket.objects.create(key=key,count=50)
        from datetime import timedelta
        RateBucket.objects.create(key='expired-admin-only',count=1,created_at=timezone.now()-timedelta(hours=2))
        response=client.post('/admin/login/', {'csrfmiddlewaretoken':token,'username':'synthetic','password':'invalid'},
                             HTTP_X_FORWARDED_FOR='forged.example.invalid')
        self.assertEqual(response.status_code,429)
        self.assertFalse(RateBucket.objects.filter(pk='expired-admin-only').exists())



@override_settings(ANTHEEC_OPERATIONAL=True, ANTHEEC_OWNER_TESTING=False,
                   ANTHEEC_PUBLIC_PREVIEW=False, MIDDLEWARE=MIDDLEWARE)
class ReleaseObservationTests(TransactionTestCase):
    def setUp(self):
        self.admin=synthetic_user('synthetic-release-primary',True)
        Authority.objects.create(primary=self.admin)

    def test_observation_is_read_only_sanitized_and_never_authorizes_release(self):
        TOTPDevice.objects.create(user=self.admin,key='ab'*20,confirmed=True)
        RecoveryCode.objects.create(user=self.admin,digest='PRIVATE-RECOVERY-DIGEST')
        before=(Audit.objects.count(),Person.objects.count())
        output=StringIO()
        with CaptureQueriesContext(connection) as queries:
            call_command('check_release_readiness',stdout=output)
        value=json.loads(output.getvalue())
        self.assertFalse(value['release_authorized'])
        self.assertEqual(value['mode'],'operational')
        self.assertTrue(value['checks']['primary_has_confirmed_totp'])
        self.assertEqual(value['approved_asset_presence'],{'signature':False,'stamp':False})
        self.assertIn('data_processing_formalities',value['unverified'])
        self.assertEqual(before,(Audit.objects.count(),Person.objects.count()))
        for secret in (self.admin.username,self.admin.password,'ab'*20,'PRIVATE-RECOVERY-DIGEST'):
            self.assertNotIn(secret,output.getvalue())
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE','ALTER','CREATE','DROP')) for q in queries))
        if connection.vendor=='postgresql':
            self.assertTrue(any(q['sql'].upper()=='SET TRANSACTION READ ONLY' for q in queries))
        with patch('governance.management.commands.check_release_readiness.Authority.objects.select_related',side_effect=RuntimeError('PRIVATE-URL')):
            with self.assertRaisesMessage(CommandError,'Observation failed') as caught:
                call_command('check_release_readiness',stdout=StringIO())
            self.assertNotIn('PRIVATE-URL',str(caught.exception))

    @override_settings(ANTHEEC_OPERATIONAL=False)
    def test_local_runtime_cannot_be_mistaken_for_hosted_readiness(self):
        with self.assertRaisesMessage(CommandError,'secure hosted'):
            call_command('check_release_readiness',stdout=StringIO())


@override_settings(ANTHEEC_OPERATIONAL=True, ANTHEEC_OWNER_TESTING=False, ANTHEEC_PUBLIC_PREVIEW=False)
class OperationalPDFTests(TestCase):
    def test_official_output_is_distinct_from_proof_and_does_not_rewrite_old_artifacts(self):
        import io
        from pypdf import PdfReader
        from . import test_pdfs as fixtures_pdf, pdf_design, pdf_services
        with override_settings(ANTHEEC_OPERATIONAL=False):
            fixtures_pdf.PDFTests.setUp(self)
            previous=pdf_services.artifact_for(self.doc.pk,'en')
            old_bytes=pdf_services.bytes_for(previous)
        from .documents import printable
        from . import services
        # An old worker omits the new column during a rolling deploy.
        from django.db.migrations.executor import MigrationExecutor
        old_model=MigrationExecutor(connection).loader.project_state([('governance','0014_translationattempt')]).apps.get_model('governance','Document')
        legacy=old_model.objects.create(kind='president_card',version=99,institutional_role_id=self.role.pk,
            token_digest='synthetic-legacy-token',code_digest='synthetic-legacy-code',
            subject_name='Synthetic Legacy',credentials=self.doc.credentials)
        from .models import Document
        self.assertTrue(Document.objects.get(pk=legacy.pk).is_specimen)
        self.assertTrue(self.doc.is_specimen)
        self.assertIn('development',printable(self.doc,'en').lower())
        old, old_metadata=pdf_design.render(self.doc,'en')
        self.assertEqual(PdfReader(io.BytesIO(old)).metadata.title,'ANTHEC SPECIMEN')
        self.assertIsNone(services.lookup_document(serial=str(self.doc.serial),code=services.decrypt(self.doc.credentials)['code']))
        result=services.replace_document(self.request,key='synthetic-release-replace',document_id=self.doc.pk,reason='Synthetic formal operational replacement')
        from .models import Document
        new=Document.objects.get(pk=result['document'])
        self.assertFalse(new.is_specimen)
        body, metadata=pdf_design.render(new,'en')
        reader=PdfReader(io.BytesIO(body))
        self.assertEqual(reader.metadata.title,'ANTHEC')
        self.assertNotIn('SPECIMEN',' '.join(page.extract_text() for page in reader.pages))
        self.assertNotIn('development',printable(new,'en').lower())
        self.assertTrue(metadata['template'].endswith('-operational-v1'))
        proof, proof_metadata=pdf_design.render(new,'en',proof=True)
        self.assertEqual(PdfReader(io.BytesIO(proof)).metadata.title,'ANTHEC SPECIMEN')
        self.assertFalse(proof_metadata['template'].endswith('-operational-v1'))
        self.assertEqual(pdf_services.bytes_for(previous),old_bytes)
        new.is_specimen=True
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):new.save()


@override_settings(ANTHEEC_OPERATIONAL=True)
class OperationalRateLimitTests(TestCase):
    def test_accounts_do_not_share_a_ten_attempt_ceiling_on_one_ingress_peer(self):
        from django.test import RequestFactory
        from .public_limits import consume
        request=RequestFactory().post('/members/login/',REMOTE_ADDR='10.0.0.1')
        for _ in range(10):self.assertTrue(consume(request,'auth',identity='first'))
        self.assertFalse(consume(request,'auth',identity='first'))
        self.assertFalse(consume(request,'auth',identity='ｆｉｒｓｔ'))
        self.assertTrue(consume(request,'auth',identity='second'))

    def test_forwarded_headers_or_peer_changes_cannot_evade_global_ceilings(self):
        from django.test import RequestFactory
        from .public_limits import consume
        from .services import digest
        from django.utils import timezone
        for scope,period,limit in (('auth',300,200),('verify',600,300),('partnership',600,50)):
            key=digest(f'operational-{scope}-global:{int(timezone.now().timestamp()//period)}')
            RateBucket.objects.create(key=key,count=limit)
            for peer in ('10.0.0.1','10.0.0.2'):
                request=RequestFactory().post('/',REMOTE_ADDR=peer,HTTP_X_FORWARDED_FOR='198.51.100.1',HTTP_CF_CONNECTING_IP='198.51.100.2')
                self.assertFalse(consume(request,scope,identity='new-account'))

    def test_verification_and_partnership_endpoints_do_not_inherit_old_peer_limits(self):
        for _ in range(31):
            self.assertEqual(self.client.post('/verify/',{'serial':'bad','code':'bad'}).status_code,404)
        for _ in range(6):
            self.assertEqual(self.client.post('/partners/request/',{}).status_code,400)

    def test_exhausted_global_auth_budget_never_creates_fresh_account_buckets(self):
        from django.test import RequestFactory
        from django.utils import timezone
        from .public_limits import consume
        from .services import digest
        moment=timezone.now()
        window=int(moment.timestamp()//300)
        key=digest(f'operational-auth-global:{window}')
        RateBucket.objects.create(key=key,count=200)
        request=RequestFactory().post('/members/login/',REMOTE_ADDR='10.0.0.1')
        with patch('governance.public_limits.timezone.now',return_value=moment):
            for index in range(100):
                self.assertFalse(consume(request,'auth',identity=f'fresh-{index}'))
        self.assertEqual(RateBucket.objects.count(),1)
        self.assertEqual(RateBucket.objects.get(pk=key).count,200)

    def test_old_counters_expire_without_resetting_active_global_or_account_limits(self):
        from datetime import timedelta
        from django.test import RequestFactory
        from django.utils import timezone
        from .public_limits import consume
        from .services import digest
        moment=timezone.now()
        with connection.cursor() as cursor:
            cursor.execute('insert into governance_ratebucket (key,count) values (%s,%s)', ['legacy-worker',1])
        self.assertIsNotNone(RateBucket.objects.get(pk='legacy-worker').created_at)
        key=digest(f'operational-auth-global:{int(moment.timestamp()//300)}')
        RateBucket.objects.create(key=key,count=200,created_at=moment)
        RateBucket.objects.create(key='old-counter',count=50,created_at=moment-timedelta(hours=2))
        RateBucket.objects.create(key='active-counter',count=10,created_at=moment-timedelta(minutes=9))
        with patch('governance.public_limits.timezone.now',return_value=moment):
            self.assertFalse(consume(RequestFactory().post('/'),'auth',identity='fresh'))
        self.assertFalse(RateBucket.objects.filter(pk='old-counter').exists())
        self.assertEqual(RateBucket.objects.get(pk='active-counter').count,10)
        self.assertEqual(RateBucket.objects.get(pk=key).count,200)
        RateBucket.objects.create(key='expired-mfa-only',count=1,created_at=moment-timedelta(hours=2))
        from .security import consume_attempt
        self.assertTrue(consume_attempt(synthetic_user('synthetic-mfa-retention')))
        self.assertFalse(RateBucket.objects.filter(pk='expired-mfa-only').exists())


@override_settings(ANTHEEC_OPERATIONAL=True,ANTHEEC_OWNER_TESTING=False,
                   ANTHEEC_PUBLIC_PREVIEW=False,ANTHEEC_APPLICATIONS_ENABLED=False)
class OperationalProfileMaintenanceTests(TestCase):
    def test_closed_applications_do_not_block_existing_member_contact_correction(self):
        from . import member_services
        from django.core.exceptions import PermissionDenied
        user=synthetic_user('synthetic-maintenance')
        person=Person.objects.create(user=user,full_name='Synthetic Before')
        member_services.update_profile(user,key='contact-correction',full_name='Synthetic After',
            contact='maintenance@example.invalid',directory_consent=False,notice=True,
            phone='0000000000',profession='Synthetic field')
        person.refresh_from_db()
        self.assertEqual(person.full_name,'Synthetic After')
        with self.assertRaises(PermissionDenied):
            member_services.submit_application(user,key='still-closed')
        with self.assertRaises(PermissionDenied):
            member_services.submit_renewal(user,key='still-closed-renewal')
        self.assertEqual(self.client.get('/members/signup/').status_code,403)
        with override_settings(ANTHEEC_PUBLIC_PREVIEW=True):
            with self.assertRaises(PermissionDenied):
                member_services.update_profile(user,key='preview-profile')
