"""Release preparation: public editorial reads cannot unlock private workflows."""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from django.http import HttpResponse
from django.urls import path
from antheec_app.urls import urlpatterns as application_urls

urlpatterns = [path("ar/unreviewed/", lambda request: HttpResponse("PRIVATE NEW ROUTE"))] + application_urls
from .deployment import (require_applications_enabled, require_payments_enabled,
                         require_issuance_enabled)
from .models import Authority, Activity, ActivityImage, Application, Payment, Document, Command, RateBucket, Person, Registration
from .tests import synthetic_user, administrative_request
from . import tests as fixtures, test_deployment as deployment_tests
from .test_deployment import PRIVATE_MIDDLEWARE
from .test_activity_editorial import content, picture
from . import services, member_services

PREVIEW_MIDDLEWARE = [
    name.replace('OwnerTestingMiddleware', 'PublicPreviewMiddleware')
    for name in PRIVATE_MIDDLEWARE
]


@override_settings(ANTHEEC_OWNER_TESTING=False, ANTHEEC_PUBLIC_PREVIEW=True,
                   MIDDLEWARE=PREVIEW_MIDDLEWARE)
class PublicPreviewTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        call_command('seed_demo', stdout=StringIO())
        self.admin = synthetic_user('synthetic-preview-owner', True)
        Authority.objects.create(primary=self.admin)
        self.other = synthetic_user('synthetic-preview-other', True)
        self.activity = Activity.objects.create(
            title='Synthetic preview', starts_on=timezone.localdate(),
            ends_on=timezone.localdate()+timedelta(days=1), capacity=20,
            presentation=content(), is_published=True)

    def test_only_editorial_reads_are_public_and_closed_links_are_not_offered(self):
        for language in ('ar', 'fr', 'en'):
            for url in ('/'+language+'/', '/activities/?lang='+language,
                        f'/activities/{self.activity.pk}/about/?lang='+language,
                        '/partners/?lang='+language):
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    head = self.client.head(url)
                    self.assertEqual(head.status_code, 200)
                    self.assertEqual(head.content, b'')
                    self.assertIn('no-store', response['Cache-Control'])
                    self.assertIn('noindex', response['X-Robots-Tag'])
                    self.assertTrue(response.context['public_preview'])
                    self.assertNotContains(response, 'href="/members/')
                    self.assertNotContains(response, 'href="/verify/')
                    self.assertNotContains(response, 'href="/partners/request/')
                    self.assertContains(response, 'aria-disabled="true"')
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.client.head('/fr/').status_code, 200)
        self.assertEqual(self.client.get('/health/').status_code, 200)
        image = ActivityImage.objects.create(activity=self.activity, jpeg=picture())
        image_url = f'/activities/{self.activity.pk}/images/{image.serial}/'
        self.assertEqual(self.client.get(image_url).status_code, 200)
        head = self.client.head(image_url)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b'')
        image.active = False
        image.save(update_fields=['active'])
        self.assertEqual(self.client.get(image_url).status_code, 404)
        image.active = True
        image.save(update_fields=['active'])
        self.activity.is_published = False
        self.activity.save(update_fields=['is_published'])
        self.assertEqual(self.client.get(f'/activities/{self.activity.pk}/about/').status_code, 404)
        self.assertEqual(self.client.get(image_url).status_code, 404)

    def test_unknown_private_and_submission_routes_stay_denied_without_writes(self):
        for url in ('/admin/', '/operations/membership/', '/members/',
                    '/members/login/', '/members/signup/', '/members/profile/',
                    '/partners/request/', f'/activities/{self.activity.pk}/',
                    '/registrations/request/', '/verify/', '/my-documents/1/',
                    '/security/enroll/', '/private-media/secret.png',
                    '/private-portraits/00000000-0000-0000-0000-000000000001/',
                    '/future-unreviewed-endpoint/'):
            for method in ('get', 'post'):
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 404)
                    self.assertIn('noindex', response['X-Robots-Tag'])
        for url in ('/ar/', '/partners/', '/activities/', f'/activities/{self.activity.pk}/about/'):
            self.assertEqual(self.client.post(url, {}).status_code, 404)
        self.assertFalse(Application.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(Document.objects.exists())
        self.assertFalse(Command.objects.exists())

    def test_public_reads_never_personalize_before_or_after_primary_mfa(self):
        private_activity = Activity.objects.create(
            title='PRIVATE UNPUBLISHED ACTIVITY', starts_on=timezone.localdate(),
            ends_on=timezone.localdate()+timedelta(days=1), capacity=20)
        for user in (self.admin, self.other):
            person = Person.objects.create(full_name='PRIVATE PARTICIPANT', user=user)
            Registration.objects.create(activity=private_activity, person=person,
                                        submitted_by=user)
            self.client.force_login(user)
            response = self.client.get('/activities/')
            self.assertEqual(response.context['mine'], [])
            self.assertNotContains(response, 'PRIVATE PARTICIPANT')
            self.assertNotContains(response, 'PRIVATE UNPUBLISHED ACTIVITY')
            self.assertEqual(self.client.get(f'/activities/{private_activity.pk}/about/').status_code, 404)
        self.http_login()
        response = self.client.get('/activities/')
        self.assertEqual(response.context['mine'], [])
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        self.assertEqual(self.client.get(f'/activities/{private_activity.pk}/about/').status_code, 404)

    def test_primary_password_alone_cannot_bypass_cms_page_restrictions(self):
        from wagtail.models import Site, PageViewRestriction
        from content.models import InstitutionalPage
        home = Site.objects.get(is_default_site=True).root_page.specific
        child = home.add_child(instance=InstitutionalPage(
            title='PRIVATE CMS TITLE', slug='restricted', live=False,
            body=[('paragraph', 'PRIVATE CMS BODY')]))
        child.save_revision().publish()
        PageViewRestriction.objects.create(page=child, restriction_type='login')
        self.client.force_login(self.admin)
        response = self.client.get('/ar/restricted/')
        self.assertNotContains(response, 'PRIVATE CMS BODY', status_code=response.status_code)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/admin/').url, '/security/challenge/')

    @override_settings(ROOT_URLCONF=__name__)
    def test_new_locale_prefixed_endpoint_is_not_accidentally_public(self):
        response = self.client.get('/ar/unreviewed/')
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'PRIVATE NEW ROUTE', status_code=404)

    def test_owner_administration_still_requires_factor_and_other_accounts_are_denied(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').url, '/security/challenge/')
        self.http_login()
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        for url in ('/verify/', '/members/apply/', '/my-documents/1/pdf/'):
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/admin/').status_code, 404)
        self.assertEqual(self.client.get('/security/enroll/').status_code, 404)

    def test_admin_login_csrf_and_global_ceiling_are_preserved(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/admin/login/', {}).status_code, 403)
        self.assertFalse(RateBucket.objects.exists())
        client.get('/admin/login/')
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        with patch('governance.deployment.timezone.now', return_value=timezone.now()):
            for i in range(51):
                result = client.post('/admin/login/', {}, HTTP_X_CSRFTOKEN=token,
                                     HTTP_X_FORWARDED_FOR=str(i))
                self.assertEqual(result.status_code, 200 if i < 50 else 429)
        self.assertEqual(RateBucket.objects.count(), 1)

    def test_preview_blocks_service_commands_even_with_accidental_true_settings(self):
        request = administrative_request(self.admin)
        with override_settings(ANTHEEC_APPLICATIONS_ENABLED=True,
                               ANTHEEC_PAYMENTS_ENABLED=True, ANTHEEC_ISSUANCE_ENABLED=True):
            operations = (
                lambda: member_services.update_profile(self.admin, key='preview'),
                lambda: services.create_application(None, 'general'),
                lambda: services.verify_payment(request, key='preview'),
                lambda: services.issue('membership_card'),
            )
            for operation in operations:
                with self.assertRaises(PermissionDenied): operation()
        self.assertFalse(Command.objects.exists())


class WorkflowSwitchTests(SimpleTestCase):
    @override_settings(ANTHEEC_OWNER_TESTING=False, ANTHEEC_PUBLIC_PREVIEW=False)
    def test_each_switch_blocks_only_its_workflow(self):
        switches = {
            'APPLICATIONS': require_applications_enabled,
            'PAYMENTS': require_payments_enabled,
            'ISSUANCE': require_issuance_enabled,
        }
        for name, guard in switches.items():
            with override_settings(**{f'ANTHEEC_{name}_ENABLED': False}):
                with self.assertRaises(PermissionDenied): guard()
                for other, other_guard in switches.items():
                    if other != name: other_guard()


class PreviewSettingsTests(SimpleTestCase):
    settings_process = deployment_tests.PrivateSettingsTests.settings_process

    def test_preview_needs_explicit_content_review_and_secure_runtime(self):
        values = {'ANTHEEC_MODE': 'public-preview', 'ANTHEEC_PUBLIC_CONTENT_APPROVED': '1'}
        result = self.settings_process(values, command=
            'from django.conf import settings as s; '
            'assert s.ANTHEEC_PUBLIC_PREVIEW and not s.ANTHEEC_OWNER_TESTING; '
            'assert not s.ANTHEEC_APPLICATIONS_ENABLED and not s.ANTHEEC_PAYMENTS_ENABLED; '
            'assert not s.ANTHEEC_ISSUANCE_ENABLED; '
            'assert "governance.deployment.PublicPreviewMiddleware" in s.MIDDLEWARE; '
            'assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; '
            'assert s.EMAIL_BACKEND.endswith("dummy.EmailBackend"); '
            'assert s.STORAGES["default"]["BACKEND"].endswith("DisabledMediaStorage")')
        self.assertEqual(result.returncode, 0, result.stderr)
        for replacement in ({'ANTHEEC_PUBLIC_CONTENT_APPROVED': None},
                            {'ANTHEEC_PUBLIC_CONTENT_APPROVED': 'true'},
                            {'DJANGO_SETTINGS_MODULE': 'antheec_app.settings.dev'},
                            {'DJANGO_SETTINGS_MODULE': 'antheec_app.settings.build'}):
            result = self.settings_process({**values, **replacement})
            self.assertNotEqual(result.returncode, 0)

    def test_hosted_modes_reject_true_or_malformed_workflow_flags(self):
        for mode in ('owner-testing', 'public-preview'):
            for name in ('APPLICATIONS', 'PAYMENTS', 'ISSUANCE'):
                for value in ('1', 'true', '', 'typo'):
                    with self.subTest(mode=mode, name=name, value=value):
                        result = self.settings_process({
                            'ANTHEEC_MODE': mode, 'ANTHEEC_PUBLIC_CONTENT_APPROVED': '1',
                            f'ANTHEEC_{name}_ENABLED': value})
                        self.assertNotEqual(result.returncode, 0)
