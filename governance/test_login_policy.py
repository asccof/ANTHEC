"""Actual login boundaries, password-only delegates and session-long primary MFA."""
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import Authority, Delegation, Person
from . import services
from .tests import synthetic_user, administrative_request


class LoginPolicyTests(TestCase):
    def setUp(self):
        self.owner = synthetic_user('synthetic-login-owner', True)
        Authority.objects.create(primary=self.owner)
        self.delegate = synthetic_user('synthetic-login-delegate')
        self.grant = Delegation.objects.create(user=self.delegate, active=True,
            capabilities=['membership.view', 'membership.approve'], epoch=5)
        call_command('seed_policy_prices', stdout=StringIO())

    def signin(self, user):
        return self.client.post('/members/login/?lang=ar', {
            'username': user.username, 'password': 'synthetic-password-123'})

    def test_delegate_password_login_workspace_navigation_and_no_mfa(self):
        response = self.signin(self.delegate)
        self.assertRedirects(response, '/operations/workspace/?lang=ar')
        self.assertEqual(self.client.session['authority_epoch'], 5)
        self.assertNotIn('otp_device_id', self.client.session)
        response = self.client.get('/members/?lang=ar')
        self.assertContains(response, 'href="/operations/workspace/?lang=ar"')
        response = self.client.get('/operations/workspace/?lang=ar')
        self.assertContains(response, '/operations/membership/')
        self.assertNotContains(response, '/operations/pricing/')
        self.assertNotContains(response, '/security/challenge/')
        self.assertEqual(self.client.get('/operations/pricing/').status_code, 403)
        person = Person.objects.create(full_name='Synthetic delegated decision', verification_notice_at=timezone.now())
        application = services.create_application(person, 'founder')
        response = self.client.post('/operations/membership.approve/', {
            'key': 'synthetic-password-only-approve', 'application_id': application.pk,
            'reason': 'Synthetic password-only delegated decision'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.state, 'approved')
        self.assertEqual(self.client.post('/operations/membership.reject/', {
            'key': 'synthetic-forbidden-reject', 'application_id': application.pk,
            'reason': 'Synthetic'}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.get('/operations/directors/').status_code, 403)
        self.assertRedirects(self.client.get('/security/challenge/'), '/operations/workspace/')
        self.assertEqual(self.client.get('/security/enroll/').status_code, 403)
        self.grant.epoch += 1
        self.grant.save()
        self.assertEqual(self.client.get('/operations/workspace/').status_code, 403)
        self.assertNotContains(self.client.get('/members/'), '/operations/workspace/')
        self.assertEqual(self.client.get('/operations/membership/').status_code, 403)
        self.client.post('/members/logout/')
        self.signin(self.delegate)
        self.assertEqual(self.client.get('/operations/workspace/').status_code, 200)
        self.grant.active = False
        self.grant.save()
        self.assertEqual(self.client.get('/operations/workspace/').status_code, 403)

    def test_primary_factor_once_per_login_and_no_time_based_rechallenge(self):
        device = TOTPDevice.objects.create(user=self.owner, confirmed=True)
        self.assertRedirects(self.signin(self.owner), '/security/challenge/?lang=ar')
        self.assertRedirects(self.client.get('/operations/workspace/'), '/security/challenge/')
        with patch('governance.security.authenticate_factor', return_value=device):
            response = self.client.post('/security/challenge/', {
                'password': 'synthetic-password-123', 'code': '123456'})
        self.assertRedirects(response, '/admin/')
        session = self.client.session
        session['reauth_at'] = 0
        session.save()
        self.assertEqual(self.client.get('/operations/directors/').status_code, 200)
        self.assertRedirects(self.client.get('/security/challenge/'), '/admin/')
        # A real sensitive command remains allowed long after the removed timer.
        request = administrative_request(self.owner)
        request.session['reauth_at'] = 0
        with transaction.atomic():
            self.assertEqual(services.authorize(request).pk, self.owner.pk)
        self.client.post('/members/logout/')
        self.signin(self.owner)
        self.assertNotIn('otp_device_id', self.client.session)
        self.assertNotIn('authority_epoch', self.client.session)
        self.assertNotContains(self.client.get('/security/challenge/'), '/operations/workspace/')
        self.assertRedirects(self.client.get('/operations/directors/'), '/security/challenge/')

    def test_grant_does_not_upgrade_an_existing_member_session(self):
        self.grant.active = False
        self.grant.save()
        self.signin(self.delegate)
        self.grant.active = True
        self.grant.save()
        self.assertNotContains(self.client.get('/members/'), '/operations/workspace/')
        self.assertEqual(self.client.get('/operations/workspace/').status_code, 403)
        self.client.post('/members/logout/')
        self.signin(self.delegate)
        self.assertEqual(self.client.get('/operations/workspace/').status_code, 200)

    def test_ordinary_member_has_no_administrative_link_or_access(self):
        member = synthetic_user('synthetic-login-member')
        self.signin(member)
        self.assertNotContains(self.client.get('/members/'), '/operations/workspace/')
        self.assertEqual(self.client.get('/operations/workspace/').status_code, 403)

    def test_native_admin_password_login_binds_delegate_without_otp(self):
        from .delegation_cms import synchronize_cms_group
        synchronize_cms_group(self.delegate, self.grant)
        response = self.client.post('/admin/login/', {
            'username': self.delegate.username, 'password': 'synthetic-password-123',
            'next': '/admin/'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['authority_epoch'], self.grant.epoch)
        self.assertNotIn('otp_device_id', self.client.session)
        self.assertRedirects(self.client.get('/admin/'), '/operations/workspace/')
