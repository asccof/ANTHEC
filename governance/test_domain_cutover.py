"""Synthetic canonical cutover: retain old QR reads without forwarding writes."""
from io import StringIO
from unittest.mock import Mock
from django.core.management import call_command, CommandError
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, RequestFactory, override_settings
from wagtail.models import Site
from .deployment import CanonicalOriginMiddleware
from .test_deployment import PrivateSettingsTests
from .test_operational_release import MIDDLEWARE


@override_settings(ALLOWED_HOSTS=['old.example.invalid', 'new.example.invalid'],
                   ANTHEEC_PUBLIC_ORIGIN='https://new.example.invalid',
                   ANTHEEC_LEGACY_ORIGIN='https://old.example.invalid')
class CanonicalRedirectTests(SimpleTestCase):
    def setUp(self):
        self.downstream = Mock(return_value=HttpResponse('current'))
        self.middleware = CanonicalOriginMiddleware(self.downstream)
        self.factory = RequestFactory()

    def test_old_verification_read_redirects_without_losing_path_or_query(self):
        for method in ('get', 'head'):
            request = getattr(self.factory, method)('/verify/?lang=fr', HTTP_HOST='old.example.invalid')
            response = self.middleware(request)
            self.assertEqual(response.status_code, 308)
            self.assertEqual(response['Location'], 'https://new.example.invalid/verify/?lang=fr')
            self.assertNotIn('#', response['Location'])
            self.assertIn('no-store', response['Cache-Control'])
            self.assertIn('noindex', response['X-Robots-Tag'])
        self.downstream.assert_not_called()

    def test_old_writes_never_reach_auth_or_business_views(self):
        for method in ('post', 'put', 'patch', 'delete', 'options'):
            request = getattr(self.factory, method)('/members/signup/', HTTP_HOST='old.example.invalid')
            self.assertEqual(self.middleware(request).status_code, 421)
        self.downstream.assert_not_called()

    def test_current_origin_and_legacy_health_are_served_normally(self):
        for host, path in [('new.example.invalid', '/ar/'), ('old.example.invalid', '/health/')]:
            request = self.factory.get(path, HTTP_HOST=host)
            self.assertEqual(self.middleware(request).content, b'current')
        self.assertEqual(self.downstream.call_count, 2)

    def test_django_accepted_host_variants_never_bypass_legacy_gate(self):
        for host in ('old.example.invalid.', 'OLD.EXAMPLE.INVALID.', 'old.example.invalid.:443'):
            with self.subTest(host=host):
                read = self.factory.get('/verify/?lang=ar', HTTP_HOST=host)
                response = self.middleware(read)
                self.assertEqual(response.status_code, 308)
                self.assertEqual(response['Location'], 'https://new.example.invalid/verify/?lang=ar')
                write = self.factory.post('/members/signup/', HTTP_HOST=host)
                self.assertEqual(self.middleware(write).status_code, 421)
        self.downstream.assert_not_called()

    def test_unlisted_host_is_rejected_before_redirect(self):
        from django.core.exceptions import DisallowedHost
        request = self.factory.get('/', HTTP_HOST='evil.example.invalid')
        with self.assertRaises(DisallowedHost):
            self.middleware(request)
        self.downstream.assert_not_called()


class CutoverSettingsTests(SimpleTestCase):
    settings_process = PrivateSettingsTests.settings_process

    def test_only_primary_is_trusted_for_csrf_and_legacy_redirect_runs_first(self):
        result = self.settings_process({
            'ANTHEEC_MODE': 'operational', 'ANTHEEC_OPERATIONAL_RELEASE_APPROVED': '1',
            'ANTHEEC_PUBLIC_CONTENT_APPROVED': '1', 'ANTHEEC_LEGACY_ORIGIN': 'https://old.example.invalid',
            'ANTHEEC_SYNC_SITE_ORIGIN': '1', 'ANTHEEC_PUBLIC_DISCOVERY_ENABLED': '1',
        }, command='from django.conf import settings as s; '
            'assert s.ALLOWED_HOSTS == ["synthetic.example.invalid", "old.example.invalid"]; '
            'assert s.CSRF_TRUSTED_ORIGINS == ["https://synthetic.example.invalid"]; '
            'assert s.MIDDLEWARE[0] == "governance.deployment.CanonicalOriginMiddleware"; '
            'assert s.ANTHEEC_SYNC_SITE_ORIGIN and s.ANTHEEC_PUBLIC_DISCOVERY_ENABLED')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preview_or_unsafe_legacy_origin_and_invalid_flags_fail_closed(self):
        for value in ('https://old.example.invalid', 'http://old.example.invalid',
                      'https://*.example.invalid', 'https://old.example.invalid:443',
                      'https://old.example.invalid/path'):
            with self.subTest(value=value):
                self.assertNotEqual(self.settings_process({'ANTHEEC_LEGACY_ORIGIN': value}).returncode, 0)
        operational = {'ANTHEEC_MODE': 'operational', 'ANTHEEC_OPERATIONAL_RELEASE_APPROVED': '1',
                       'ANTHEEC_PUBLIC_CONTENT_APPROVED': '1'}
        for value in ('http://old.example.invalid', 'https://*.example.invalid',
                      'https://old.example.invalid:443', 'https://old.example.invalid/path',
                      'https://synthetic.example.invalid'):
            self.assertNotEqual(self.settings_process({**operational, 'ANTHEEC_LEGACY_ORIGIN': value}).returncode, 0)
        for flag in ('ANTHEEC_SYNC_SITE_ORIGIN', 'ANTHEEC_PUBLIC_DISCOVERY_ENABLED'):
            for value in ('1', 'true'):
                self.assertNotEqual(self.settings_process({flag: value}).returncode, 0)


@override_settings(ANTHEEC_OPERATIONAL=True, ANTHEEC_PUBLIC_ORIGIN='https://new.example.invalid')
class SiteOriginTests(TestCase):
    def setUp(self):
        call_command('seed_demo', verbosity=0, stdout=StringIO())
        self.site = Site.objects.get(is_default_site=True)

    def test_plan_does_not_write_and_apply_is_idempotent_preserving_pages(self):
        before = (self.site.hostname, self.site.port, self.site.root_page_id)
        call_command('sync_site_origin', stdout=StringIO())
        self.site.refresh_from_db()
        self.assertEqual((self.site.hostname, self.site.port, self.site.root_page_id), before)
        for _ in range(2):
            call_command('sync_site_origin', apply=True, stdout=StringIO())
        self.site.refresh_from_db()
        self.assertEqual((self.site.hostname, self.site.port), ('new.example.invalid', 443))
        self.assertEqual(self.site.root_page_id, before[2])
        self.assertEqual(self.site.root_url, 'https://new.example.invalid')

    @override_settings(ANTHEEC_OPERATIONAL=False)
    def test_apply_outside_operational_fails(self):
        with self.assertRaises(CommandError):
            call_command('sync_site_origin', apply=True, stdout=StringIO())

    def test_existing_site_collision_is_rejected_without_mutating_default(self):
        Site.objects.create(hostname='new.example.invalid', port=443, root_page=self.site.root_page)
        before = (self.site.hostname, self.site.port)
        with self.assertRaises(CommandError):
            call_command('sync_site_origin', apply=True, stdout=StringIO())
        self.site.refresh_from_db()
        self.assertEqual((self.site.hostname, self.site.port), before)


@override_settings(ANTHEEC_OPERATIONAL=True, MIDDLEWARE=MIDDLEWARE,
                   ANTHEEC_PUBLIC_DISCOVERY_ENABLED=True, ANTHEEC_PRIVACY_NOTICE_ENABLED=False)
class PublicDiscoveryTests(TestCase):
    def setUp(self):
        call_command('seed_demo', verbosity=0, stdout=StringIO())

    def test_successful_editorial_pages_index_but_accounts_verification_errors_do_not(self):
        for language in ('ar', 'fr', 'en'):
            response = self.client.get(f'/{language}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['X-Robots-Tag'], 'index, follow')
            self.assertIn('no-store', response['Cache-Control'])
        for path in ('/verify/', '/members/signup/', '/admin/login/', '/health/', '/ar/missing/'):
            response = self.client.get(path)
            self.assertIn('noindex', response['X-Robots-Tag'], path)

    def test_authenticated_editorial_responses_remain_unindexed(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user('synthetic-domain-member')
        self.client.force_login(user)
        self.assertIn('noindex', self.client.get('/ar/')['X-Robots-Tag'])

    @override_settings(ANTHEEC_PUBLIC_DISCOVERY_ENABLED=False)
    def test_discovery_defaults_remain_closed(self):
        self.assertIn('noindex', self.client.get('/ar/')['X-Robots-Tag'])
