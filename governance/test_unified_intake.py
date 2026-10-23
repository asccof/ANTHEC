"""Atomic one-submit registration and existing-account intake, synthetic only."""
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from bs4 import BeautifulSoup
from .intake_test_support import signup_payload
from .models import Person, Application, Portrait, Audit, Membership, Document, Command
from .tests import synthetic_user
from .privacy_notice import VERSION


@override_settings(ANTHEEC_PRIVACY_NOTICE_ENABLED=True, ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON='2026-10-22')
class UnifiedIntakeTests(TestCase):
    def setUp(self):
        call_command('seed_policy_prices', stdout=StringIO())

    def payload(self, username='synthetic-unified', lang='ar', **changes):
        data = signup_payload(username, privacy_acceptance='on', privacy_version=VERSION,
                              privacy_language=lang)
        data.update(changes)
        return data

    def test_one_form_in_all_languages_with_unique_fields_and_unchecked_consents(self):
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get('/members/signup/?lang='+lang)
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.select_one('#membership-intake')
            self.assertEqual(len(soup.select('main form')), 1)
            self.assertEqual(len(form.select('fieldset')), 4)
            self.assertEqual(soup.html['dir'], 'rtl' if lang == 'ar' else 'ltr')
            for name in ('username', 'password1', 'password2', 'full_name', 'phone', 'profession',
                         'tier', 'applicant_capacity', 'photo', 'notice', 'photo_consent',
                         'privacy_acceptance', 'privacy_version', 'privacy_language', 'key'):
                self.assertEqual(len(form.select('[name="'+name+'"]')), 1, (lang, name))
            for name in ('notice', 'photo_consent', 'privacy_acceptance', 'directory_consent'):
                self.assertNotIn('checked', form.select_one('[name="'+name+'"]').attrs)

    def test_one_submit_creates_private_pending_request_and_signs_in_with_receipt(self):
        response = self.client.post('/members/signup/?lang=fr', self.payload(lang='fr'), follow=True)
        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.get(username='synthetic-unified')
        person = Person.objects.get(user=user)
        app = Application.objects.get(person=person)
        self.assertEqual(app.state, 'submitted')
        self.assertEqual(app.quote, 500)
        self.assertEqual(app.intake_portrait.state, 'pending')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertFalse(user.is_staff or user.is_superuser or user.user_permissions.exists())
        self.assertFalse(Membership.objects.exists() or Document.objects.exists())
        self.assertContains(response, 'Votre demande d’adhésion a été reçue')
        self.assertIn('/members/applications/', response.request['PATH_INFO'])
        self.assertEqual(Audit.objects.filter(actor=user, action='privacy.acknowledged').count(), 4)
        # Retrying after the successful login only returns the existing request.
        self.assertEqual(self.client.post('/members/signup/', self.payload()).status_code, 302)
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(Person.objects.count(), 1)

    def test_invalid_subforms_or_photo_never_leave_an_account_or_partial_evidence(self):
        for changes in ({'phone':'bad'}, {'tier':'invalid'}, {'notice':''}, {'photo_consent':''},
                        {'password2':'different'}, {'privacy_version':'obsolete'}):
            response = self.client.post('/members/signup/', self.payload(**changes))
            self.assertEqual(response.status_code, 400)
            self.assertFalse(get_user_model().objects.filter(username='synthetic-unified').exists())
            self.assertFalse(Person.objects.exists() or Application.objects.exists() or Portrait.objects.exists())
            self.assertFalse(Audit.objects.filter(action='privacy.acknowledged').exists())
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = self.client.post('/members/signup/', self.payload(photo=SimpleUploadedFile('bad.png', b'bad')))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='synthetic-unified').exists())

    def test_service_failure_rolls_back_account_profile_portrait_and_audit(self):
        from . import services
        original = services.create_application
        def fail_after_creation(*args, **kwargs):
            original(*args, **kwargs)
            raise ValidationError('synthetic failure after portrait and application')
        with patch('governance.services.create_application', side_effect=fail_after_creation):
            response = self.client.post('/members/signup/', self.payload())
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='synthetic-unified').exists())
        for model in (Person, Application, Portrait, Command, Audit):
            self.assertEqual(model.objects.count(), 0, model.__name__)

    def test_existing_account_without_profile_can_complete_everything_in_one_submit(self):
        user = synthetic_user('synthetic-existing-unified')
        self.client.force_login(user)
        response = self.client.get('/members/apply/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="password1"')
        response = self.client.post('/members/apply/', self.payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Person.objects.get().user_id, user.pk)
        self.assertEqual(Application.objects.count(), 1)
        self.assertFalse(get_user_model().objects.filter(username='synthetic-unified').exists())

    def test_csrf_duplicate_username_and_workflow_guards(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/members/signup/', self.payload()).status_code, 403)
        user = synthetic_user('synthetic-unified')
        self.assertEqual(self.client.post('/members/signup/', self.payload()).status_code, 400)
        self.assertFalse(Person.objects.exists() or Application.objects.exists())
        with override_settings(ANTHEEC_APPLICATIONS_ENABLED=False):
            self.assertEqual(self.client.get('/members/signup/').status_code, 403)
            self.client.force_login(user)
            self.assertEqual(self.client.get('/members/apply/').status_code, 403)

    def test_fee_reminder_uses_effective_prices_and_does_not_require_payment(self):
        from .models import Price, Payment
        from django.utils import timezone
        from datetime import timedelta
        Price.objects.create(tier='affiliate', amount=725, starts_at=timezone.now()-timedelta(seconds=1))
        Price.objects.create(tier='affiliate', amount=999, starts_at=timezone.now()+timedelta(days=1))
        for lang in ('ar', 'fr', 'en'):
            response = self.client.get('/members/signup/?lang='+lang)
            fees = {item['tier']: item for item in response.context['fee_choices']}
            self.assertEqual(fees['affiliate']['amount'], 725)
            self.assertEqual(fees['founder']['amount'], 0)
            self.assertEqual(fees['honorary']['amount'], 0)
            self.assertContains(response, 'data-fee-tier="affiliate"')
            self.assertContains(response, response.context['labels']['fee_contact'])
        response = self.client.post('/members/signup/?lang=en', self.payload(lang='en'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Application.objects.get().quote, 725)
        self.assertFalse(Payment.objects.exists())
        self.assertContains(response, response.context['labels']['pending_fee_contact'])
        # Receipt continues showing the submitted quote after later price changes.
        Price.objects.create(tier='affiliate', amount=800, starts_at=timezone.now())
        receipt = self.client.get(response.request['PATH_INFO']+'?lang=en')
        self.assertEqual(receipt.context['app'].quote, 725)
        self.assertContains(receipt, receipt.context['labels']['pending_fee_contact'])

    def test_documented_exemption_or_verified_payment_suppresses_payment_prompt(self):
        from .models import Exemption, Payment
        response = self.client.post('/members/signup/?lang=en', self.payload(lang='en'), follow=True)
        app = Application.objects.get()
        user = app.person.user
        url = response.request['PATH_INFO']+'?lang=en'
        Payment.objects.create(application=app, amount=app.quote, method='cash',
                               verified_by=user, proof_reference='Synthetic payment')
        receipt = self.client.get(url)
        self.assertNotContains(receipt, receipt.context['labels']['pending_fee_contact'])
        self.assertContains(receipt, receipt.context['labels']['application_received'])
        self.assertFalse(receipt.context['fee_exempt'])
        from .models import Refund
        payment = Payment.objects.get(application=app)
        Refund.objects.create(payment=payment, amount=app.quote, approved=True, actor=user, reason='Synthetic refund')
        self.assertContains(self.client.get(url), receipt.context['labels']['pending_fee_contact'])
        Exemption.objects.create(application=app, actor=user, reason='Synthetic exception')
        receipt = self.client.get(url)
        self.assertNotContains(receipt, receipt.context['labels']['pending_fee_contact'])
        self.assertContains(receipt, receipt.context['labels']['fee_exempt'])
        app.refresh_from_db()
        self.assertEqual(app.quote, 500)
