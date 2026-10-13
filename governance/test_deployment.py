"""Synthetic regression coverage for the temporary private deployment boundary."""
import os
import secrets
import subprocess
import sys
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.test import Client, TestCase, SimpleTestCase, override_settings
from .deployment import OwnerTestingMiddleware, DisabledMediaStorage
from .models import Authority, Delegation, Document, Application, Payment, RateBucket
from .tests import synthetic_user, administrative_request
from . import tests as fixtures
from . import services as s, pdf_services
from .documents import render_outbox

PRIVATE_MIDDLEWARE = list(settings.MIDDLEWARE)
PRIVATE_MIDDLEWARE.insert(PRIVATE_MIDDLEWARE.index("governance.middleware.AdminSecurityMiddleware"),
                          "governance.deployment.OwnerTestingMiddleware")


@override_settings(ANTHEEC_OWNER_TESTING=True, MIDDLEWARE=PRIVATE_MIDDLEWARE)
class OwnerDeploymentTests(TestCase):
    http_login = fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin = synthetic_user("synthetic-owner", True)
        Authority.objects.create(primary=self.admin)
        self.other = synthetic_user("synthetic-other", True)

    def test_anonymous_cannot_read_or_register(self):
        for url in ("/", "/ar/", "/fr/", "/en/", "/admin/", "/security/enroll/",
                    "/members/signup/", "/members/apply/", "/registrations/request/",
                    "/verify/", "/my-documents/1/", "/private-media/secret.png",
                    "/private-certificate-assets/00000000-0000-0000-0000-000000000001/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertIn("no-store", response["Cache-Control"])
                self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertEqual(self.client.post("/members/signup/", {}).status_code, 404)
        self.assertEqual(self.client.get("/health/").json(), {"project": "ANTHEC", "status": "ok"})
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)

    def test_mfa_html_policy_and_https_form_csrf_in_all_languages(self):
        # The HTML policy overrides the HTTP header in real browsers.
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for language in ("ar", "fr", "en"):
            for path in ("/security/enroll/", "/security/challenge/"):
                with self.subTest(language=language, path=path):
                    url = path + "?lang=" + language
                    response = client.get(url, secure=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, '<meta name="referrer" content="same-origin">')
                    self.assertNotContains(response, 'content="no-referrer"')
                    token = client.cookies[settings.CSRF_COOKIE_NAME].value
                    payload = {"csrfmiddlewaretoken": token, "password": "invalid-synthetic-password", "code": ""}
                    response = client.post(url, payload, secure=True,
                                           HTTP_REFERER="https://testserver" + url)
                    self.assertEqual(response.status_code, 200)
                    # A valid token must still fail for a foreign source.
                    response = client.post(url, payload, secure=True,
                                           HTTP_ORIGIN="https://foreign.example.invalid")
                    self.assertEqual(response.status_code, 403)

    def test_no_delegate_or_unbootstrapped_superuser_access(self):
        Delegation.objects.create(user=self.other, active=True, epoch=1)
        self.http_login(self.other, epoch=1)
        self.assertEqual(self.client.get("/admin/").status_code, 404)
        self.assertEqual(self.client.get("/security/enroll/").status_code, 404)
        Authority.objects.all().delete()
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_owner_must_enroll_verify_and_keep_session_epoch(self):
        self.client.force_login(self.admin)
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/security/challenge/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/security/enroll/").status_code, 200)
        self.http_login()
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        for url in ("/members/signup/", "/members/apply/", "/members/renew/",
                    "/verify/", "/my-documents/1/pdf/"):
            self.assertEqual(self.client.get(url).status_code, 404)
        session = self.client.session
        session["authority_epoch"] = 9
        session.save()
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_inactive_owner_is_denied(self):
        self.http_login()
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_verified_owner_root_redirect_keeps_locale_and_private_headers(self):
        self.http_login()
        for language in ("ar", "fr", "en"):
            response = self.client.get("/", HTTP_ACCEPT_LANGUAGE=language)
            self.assertRedirects(response, f"/{language}/", fetch_redirect_response=False)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertIn("noindex", response["X-Robots-Tag"])

    def test_login_throttle_does_not_trust_forwarding_header(self):
        from django.test import Client
        from django.utils import timezone
        client = Client(enforce_csrf_checks=True)
        client.get("/admin/login/")
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        # The same Render ingress peer must not impose an unintended ten-
        # request ceiling; forged forwarding headers cannot create new buckets.
        with patch("governance.deployment.timezone.now", return_value=timezone.now()):
            for i in range(51):
                response = client.post("/admin/login/", {}, HTTP_X_CSRFTOKEN=token,
                                       REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=str(i))
                self.assertEqual(response.status_code, 200 if i < 50 else 429)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertEqual(RateBucket.objects.count(), 1)
        self.assertEqual(RateBucket.objects.get().count, 51)

    def test_invalid_csrf_requests_do_not_exhaust_owner_login_budget(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        for _ in range(60):
            self.assertEqual(client.post("/admin/login/", {}).status_code, 403)
        self.assertFalse(RateBucket.objects.exists())
        client.get("/admin/login/")
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(client.post("/admin/login/", {}, HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(RateBucket.objects.get().count, 1)

    def test_commands_and_renderer_fail_before_any_write(self):
        request = administrative_request(self.admin)
        operations = [
            lambda: s.create_application(None, "general"),
            lambda: s.register(None, None, self.admin),
            lambda: s.issue("membership_card"),
            lambda: s.issue("participation_certificate"),
            lambda: s.verify_payment(request, key="test", application_id=1,
                                     amount="100", method="cash", proof_reference="synthetic"),
            lambda: s.decide_refund(request, key="refund", payment_id=1,
                                     amount="100", approved=True, reason="synthetic"),
            lambda: pdf_services.artifact_for(1),
            lambda: render_outbox(1),
        ]
        for operation in operations:
            with self.assertRaises(PermissionDenied):
                operation()
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    def test_ephemeral_media_cannot_be_saved_opened_or_linked(self):
        storage = DisabledMediaStorage()
        with self.assertRaises(PermissionDenied):
            storage.save("signature.png", ContentFile(b"synthetic"))
        with self.assertRaises(PermissionDenied):
            storage.open("signature.png")
        with self.assertRaises(PermissionDenied):
            storage.url("signature.png")


class PrivateSettingsTests(SimpleTestCase):
    def settings_process(self, replacements=None, command=None):
        environment = dict(os.environ)
        environment.update({
            "DJANGO_SETTINGS_MODULE": "antheec_app.settings.production",
            "ANTHEEC_MODE": "owner-testing",
            "ANTHEEC_SECRET_KEY": secrets.token_urlsafe(64),
            "ANTHEEC_DATA_KEY": Fernet.generate_key().decode(),
            "ANTHEEC_PUBLIC_ORIGIN": "https://synthetic.example.invalid",
            "DATABASE_URL": "postgresql://synthetic:synthetic@localhost/anthec_owner_testing",
        })
        for key, value in (replacements or {}).items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        return subprocess.run([sys.executable, "-c", command or
            "from django.conf import settings as s; "
            "assert not s.DEBUG and s.ANTHEEC_OWNER_TESTING; "
            "assert s.ALLOWED_HOSTS == ['synthetic.example.invalid']; "
            "assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; "
            "assert s.SECURE_REFERRER_POLICY == 'same-origin'; "
            "assert s.DATABASES['default']['OPTIONS']['sslmode'] == 'require'; "
            "assert s.EMAIL_BACKEND.endswith('dummy.EmailBackend'); "
            "assert not s.WHITENOISE_AUTOREFRESH and not s.WHITENOISE_USE_FINDERS"],
            cwd=settings.BASE_DIR, env=environment, capture_output=True, text=True, timeout=60)

    def test_secure_private_settings_load_without_contacting_database(self):
        result = self.settings_process()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_render_generated_database_suffix_is_used_without_widening_namespace(self):
        result = self.settings_process(
            {"DATABASE_URL": "postgresql://synthetic:synthetic@localhost/anthec_owner_testing_a1b2"},
            command="from django.conf import settings as s; "
                    "assert s.DATABASES['default']['NAME'] == 'anthec_owner_testing_a1b2'")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_secrets_other_database_and_unsafe_origin_fail_closed(self):
        bad = [
            {"DJANGO_SETTINGS_MODULE": "antheec_app.settings.dev"},
            {"DJANGO_SETTINGS_MODULE": "antheec_app.settings.build"},
            {"ANTHEEC_MODE": "production"}, {"ANTHEEC_MODE": None},
            {"ANTHEEC_SECRET_KEY": None}, {"ANTHEEC_SECRET_KEY": "a" * 70},
            {"ANTHEEC_DATA_KEY": None}, {"ANTHEEC_DATA_KEY": "invalid"},
            {"ANTHEEC_DATA_KEY": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="},
            {"ANTHEEC_DATA_KEY": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=\n"},
            {"ANTHEEC_DATA_KEY": " MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="},
            {"DATABASE_URL": "postgresql://synthetic:synthetic@localhost/tighri"},
            {"DATABASE_URL": "postgresql://synthetic:synthetic@localhost/anthec_owner_testing/tighri"},
            {"DATABASE_URL": "postgresql://synthetic:synthetic@localhost/anthec_owner_testing.evil"},
            {"DATABASE_URL": "sqlite:///db.sqlite3"}, {"DATABASE_URL": None},
            {"ANTHEEC_PUBLIC_ORIGIN": "http://synthetic.example.invalid"},
            {"ANTHEEC_PUBLIC_ORIGIN": "https://*.example.invalid"},
            {"ANTHEEC_PUBLIC_ORIGIN": "https://example.invalid/path"},
        ]
        for values in bad:
            with self.subTest(keys=list(values)):
                self.assertNotEqual(self.settings_process(values).returncode, 0)

    def test_deployment_checks_have_only_deliberately_staged_hsts_warnings(self):
        result = self.settings_process(command=
            "import django; django.setup(); "
            "from django.core.checks import run_checks; "
            "issues=run_checks(include_deployment_checks=True); "
            "assert {x.id for x in issues} == {'security.W005', 'security.W021'}, "
            "[(x.id, str(x)) for x in issues]")
        self.assertEqual(result.returncode, 0, result.stderr)
