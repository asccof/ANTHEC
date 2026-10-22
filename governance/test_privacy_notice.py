import hashlib
import json
import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone, translation
from . import privacy_notice as privacy, member_services, services
from .models import Audit, Person, Activity, Registration, PartnershipRequest, Application
from .tests import synthetic_user
from .member_forms import SignupForm
from .member_labels import vocabulary
from .intake_test_support import intake_payload


def acknowledgement(language='ar'):
    return {'privacy_acceptance': True, 'privacy_version': privacy.VERSION, 'privacy_language': language}


@override_settings(ANTHEEC_PRIVACY_NOTICE_ENABLED=True, ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON='2026-10-22')
class PrivacyNoticeTests(TestCase):
    def setUp(self):
        self.user = synthetic_user('synthetic-privacy')

    def profile(self, **changes):
        data = dict(full_name='Synthetic Privacy', contact='synthetic@example.invalid',
            phone='+212600000001', profession='Synthetic coach', directory_consent=False, notice=True)
        data.update(changes)
        return member_services.update_profile(self.user, key=str(uuid.uuid4()), **data)

    def test_profile_requires_current_explicit_acknowledgement_at_service_boundary(self):
        for data in ({}, {**acknowledgement(), 'privacy_acceptance': False},
                     {**acknowledgement(), 'privacy_version': 'obsolete'},
                     {**acknowledgement(), 'privacy_language': 'unknown'}):
            with self.assertRaises(ValidationError):
                self.profile(**data)
        self.assertFalse(Person.objects.exists())
        self.assertFalse(Audit.objects.filter(action='privacy.acknowledged').exists())

    def test_exact_notice_snapshot_and_idempotency_are_preserved(self):
        data = dict(full_name='Synthetic Privacy', contact='', directory_consent=False, notice=True,
                    **acknowledgement('fr'))
        key = str(uuid.uuid4())
        first = member_services.update_profile(self.user, key=key, **data)
        self.assertEqual(member_services.update_profile(self.user, key=key, **data), first)
        row = Audit.objects.get(action='privacy.acknowledged')
        self.assertEqual(row.actor, self.user)
        self.assertEqual(row.details['purpose'], 'member.profile')
        notice = row.details['notice']
        self.assertEqual(notice['language'], 'fr')
        digest = notice.pop('sha256')
        self.assertEqual(digest, hashlib.sha256(json.dumps(notice, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
        self.assertEqual(notice['version'], privacy.VERSION)
        self.assertEqual(notice['published_on'], '2026-10-22')
        self.assertEqual(len(notice['sections']), 6)
        self.assertEqual(set(row.details), {'purpose', 'notice'})
        self.assertIsNotNone(row.created_at)

    def test_notice_and_unchecked_separate_signup_acknowledgement_in_all_languages(self):
        for language in ('ar', 'fr', 'en'):
            response = self.client.get('/privacy/?lang=' + language)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, privacy.WORDS[language][0])
            self.assertContains(response, privacy.VERSION)
            self.assertIn('no-store', response['Cache-Control'])
            with translation.override(language):
                form = SignupForm(labels=vocabulary(language)[1])
            self.assertEqual(form.fields['privacy_acceptance'].label, privacy.WORDS[language][1])
            self.assertFalse(form.fields['privacy_acceptance'].initial)
            self.assertIn('/privacy/?lang='+language, str(form.fields['privacy_acceptance'].help_text))
            self.assertEqual(form['privacy_language'].value(), language)
        self.assertEqual(self.client.post('/privacy/').status_code, 405)

    def test_signup_does_not_create_account_until_acknowledged(self):
        data = dict(username='synthetic-privacy-signup', password1='Synthetic-long-567!pass',
                    password2='Synthetic-long-567!pass')
        self.assertEqual(self.client.post('/members/signup/?lang=en', data).status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username=data['username']).exists())
        response = self.client.post('/members/signup/?lang=en', {**data, **acknowledgement('en')})
        self.assertEqual(response.status_code, 302)
        actor = get_user_model().objects.get(username=data['username'])
        row = Audit.objects.get(action='privacy.acknowledged', actor=actor)
        self.assertEqual(row.details['purpose'], 'member.signup')
        self.assertEqual(row.details['notice']['language'], 'en')

    def test_anonymous_partnership_request_keeps_separate_acknowledgements(self):
        data = dict(organization='Synthetic organization', contact_email='synthetic@example.invalid',
                    message='Synthetic proposal', notice_acknowledged=True)
        self.assertEqual(self.client.post('/partners/request/?lang=fr', data).status_code, 400)
        self.assertFalse(PartnershipRequest.objects.exists())
        self.assertEqual(self.client.post('/partners/request/?lang=fr', {**data, **acknowledgement('fr')}).status_code, 302)
        row = PartnershipRequest.objects.get()
        evidence = Audit.objects.get(action='privacy.acknowledged')
        self.assertIsNone(evidence.actor)
        self.assertEqual(evidence.subject, f'partnership.request:{row.pk}')
        self.assertTrue(row.notice_acknowledged)

    def test_activity_registration_and_application_cannot_skip_acknowledgement(self):
        self.profile(**acknowledgement())
        person = Person.objects.get(user=self.user)
        day = timezone.localdate()
        activity = Activity.objects.create(title='Synthetic privacy activity', starts_on=day, ends_on=day, capacity=5)
        with self.assertRaises(ValidationError):
            services.register(activity, person, self.user)
        registration = services.register(activity, person, self.user, **acknowledgement())
        self.assertEqual(Registration.objects.count(), 1)
        self.assertTrue(Audit.objects.filter(action='privacy.acknowledged', subject=f'activity.registration:{registration.pk}').exists())
        call_command('seed_policy_prices', verbosity=0)
        data = dict(tier='general', applicant_capacity='other', capacity_other='Synthetic role', **intake_payload())
        with self.assertRaises(ValidationError):
            member_services.submit_application(self.user, key=str(uuid.uuid4()), **data)
        self.assertFalse(Application.objects.exists())
        member_services.submit_application(self.user, key=str(uuid.uuid4()), **data, **acknowledgement())
        self.assertTrue(Audit.objects.filter(action='privacy.acknowledged', actor=self.user,
                                            details__purpose='member.application').exists())

    def test_invalid_publication_date_fails_closed(self):
        for value in ('', '2099-01-01'):
            with override_settings(ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON=value):
                with self.assertRaises(ImproperlyConfigured):
                    privacy.enabled()

    @override_settings(ANTHEEC_OPERATIONAL=True, ANTHEEC_OWNER_TESTING=False,
                       ANTHEEC_PUBLIC_PREVIEW=False)
    def test_password_only_primary_can_read_anonymous_notice(self):
        from .models import Authority
        from .test_operational_release import MIDDLEWARE
        self.enableOperationalMiddleware = override_settings(MIDDLEWARE=MIDDLEWARE)
        self.enableOperationalMiddleware.enable()
        self.addCleanup(self.enableOperationalMiddleware.disable)
        Authority.objects.create(primary=self.user)
        self.client.force_login(self.user)
        for method in (self.client.get, self.client.head):
            response = method('/privacy/?lang=fr')
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.wsgi_request.user.is_authenticated)
            self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.get('/admin/').url, '/security/challenge/')

    def test_portrait_and_renewal_service_boundaries_cannot_skip_notice(self):
        from . import portraits
        with self.assertRaises(ValidationError):
            portraits.upload_portrait(self.user, key=str(uuid.uuid4()), person_id=999,
                                      image_data='', consent=True)
        with self.assertRaises(ValidationError):
            member_services.submit_renewal(self.user, key=str(uuid.uuid4()), membership_id=999)

    def test_registration_json_requires_and_accepts_the_same_versioned_evidence(self):
        self.profile(**acknowledgement())
        person = Person.objects.get(user=self.user)
        day = timezone.localdate()
        activity = Activity.objects.create(title='Synthetic API activity', starts_on=day, ends_on=day, capacity=2)
        self.client.force_login(self.user)
        data = {'person_id': person.pk, 'activity_id': activity.pk}
        self.assertEqual(self.client.post('/registrations/request/', data=json.dumps(data), content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/registrations/request/', data=json.dumps({**data, **acknowledgement()}), content_type='application/json').status_code, 201)

    @override_settings(ANTHEEC_PRIVACY_NOTICE_ENABLED=False)
    def test_staged_feature_is_closed_and_does_not_change_existing_forms(self):
        self.assertEqual(self.client.get('/privacy/').status_code, 404)
        self.assertNotIn('privacy_acceptance', SignupForm(labels=vocabulary('ar')[1]).fields)
        self.profile()
        self.assertFalse(Audit.objects.filter(action='privacy.acknowledged').exists())


class PrivacyHostedSettingsTests(TestCase):
    def test_activation_is_explicit_operational_and_dated(self):
        from .test_deployment import PrivateSettingsTests
        run = PrivateSettingsTests('test_secure_private_settings_load_without_contacting_database').settings_process
        base = {'ANTHEEC_MODE': 'operational', 'ANTHEEC_OPERATIONAL_RELEASE_APPROVED': '1',
                'ANTHEEC_PUBLIC_CONTENT_APPROVED': '1', 'ANTHEEC_PRIVACY_NOTICE_ENABLED': '1'}
        self.assertNotEqual(run(base).returncode, 0)
        self.assertNotEqual(run({**base, 'ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON': 'invalid'}).returncode, 0)
        self.assertNotEqual(run({**base, 'ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON': '2099-01-01'}).returncode, 0)
        self.assertEqual(run({**base, 'ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON': '2026-10-22'},
                            command='from django.conf import settings as s; assert s.ANTHEEC_PRIVACY_NOTICE_ENABLED').returncode, 0)
        self.assertNotEqual(run({'ANTHEEC_PRIVACY_NOTICE_ENABLED': '1',
                                'ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON': '2026-10-22'}).returncode, 0)
