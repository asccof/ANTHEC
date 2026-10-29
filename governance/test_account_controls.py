import uuid
from io import StringIO
from django.test import TestCase,Client
from django.core.management import call_command
from django.core.exceptions import PermissionDenied,ValidationError
from bs4 import BeautifulSoup
from . import tests as fixtures,account_services as service
from .models import Authority,Person,Delegation,MemberAccountControl,Audit,Application


class AccountControlsTests(TestCase):
    http_login=fixtures.PolicyTests.http_login

    def setUp(self):
        self.admin=fixtures.synthetic_user('synthetic-account-owner',True)
        Authority.objects.create(primary=self.admin)
        self.request=fixtures.administrative_request(self.admin)
        self.holder=fixtures.synthetic_user('synthetic-account-member')
        self.person=Person.objects.create(user=self.holder,full_name='Synthetic Member')
        self.url=f'/operations/accounts/{self.holder.pk}/'
        self.http_login()

    def decide(self,state='suspended',epoch=0,**extra):
        return self.client.post(self.url,dict(action=state,key=str(uuid.uuid4()),expected_epoch=epoch,confirm='on',**extra))

    def test_state_action_requires_only_confirmation_not_profile_or_password(self):
        response=self.client.get(self.url+'?lang=ar')
        soup=BeautifulSoup(response.content,'html.parser')
        for form in soup.select('.account-state-form'):
            self.assertEqual(set(field.get('name') for field in form.select('input,textarea')),
                             {'csrfmiddlewaretoken','action','key','expected_epoch','confirm','reason'})
        ids=[tag['id'] for tag in soup.select('[id]')]
        self.assertEqual(len(ids),len(set(ids)))
        from django.urls import reverse
        native=self.client.get(reverse('wagtailusers_users:edit',args=[self.holder.pk]))
        self.assertEqual(native.status_code,302)
        self.assertIn(self.url,native.url)
        original=self.holder.password
        self.assertEqual(self.decide().status_code,302)
        self.holder.refresh_from_db()
        self.assertFalse(self.holder.is_active)
        self.assertEqual(self.holder.password,original)
        self.assertEqual(MemberAccountControl.objects.get(user=self.holder).state,'suspended')
        self.assertEqual(self.decide('active',epoch=1).status_code,302)
        self.holder.refresh_from_db();self.assertTrue(self.holder.is_active)
        self.assertEqual(self.decide('cancelled',epoch=2).status_code,302)
        self.assertTrue(Person.objects.filter(pk=self.person.pk).exists())
        self.assertEqual(Audit.objects.filter(action='account.state.changed').count(),3)

    def test_disabled_login_and_sessions_stay_revoked_after_reactivation(self):
        member=Client();member.force_login(self.holder)
        service.change_state(self.request,key=str(uuid.uuid4()),user_id=self.holder.pk,state='suspended',expected_epoch=0,confirm=True)
        self.assertEqual(member.get('/members/profile/').status_code,302)
        service.change_state(self.request,key=str(uuid.uuid4()),user_id=self.holder.pk,state='active',expected_epoch=1,confirm=True)
        self.assertEqual(member.get('/members/profile/').status_code,302)
        # A pre-disable session never used while disabled must also fail after reactivation.
        old=Client();old.force_login(self.holder)
        service.change_state(self.request,key=str(uuid.uuid4()),user_id=self.holder.pk,state='suspended',expected_epoch=2,confirm=True)
        self.assertEqual(old.post('/members/login/',{'username':self.holder.username,'password':'not-the-password'}).status_code,400)
        service.change_state(self.request,key=str(uuid.uuid4()),user_id=self.holder.pk,state='active',expected_epoch=3,confirm=True)
        self.assertEqual(old.get('/members/profile/').status_code,302)
        self.holder.set_password('Synthetic-new-login-42!');self.holder.save(update_fields=['password'])
        fresh=Client()
        self.assertEqual(fresh.post('/members/login/',{'username':self.holder.username,'password':'Synthetic-new-login-42!'}).status_code,302)
        self.assertEqual(fresh.get('/members/profile/').status_code,200)

    def test_edit_blank_account_names_email_and_preserve_credentials_rights(self):
        response=self.client.post(self.url,dict(action='edit',key=str(uuid.uuid4()),expected_epoch=0,confirm='on',
            username='synthetic-account-renamed',email='',first_name='',last_name='',full_name='Corrected Synthetic Member',
            phone='+212600000001',contact='synthetic@example.invalid',profession='Synthetic coach'))
        self.assertEqual(response.status_code,302)
        original=self.holder.password
        self.holder.refresh_from_db();self.person.refresh_from_db()
        self.assertEqual(self.holder.username,'synthetic-account-renamed')
        self.assertEqual(self.person.full_name,'Corrected Synthetic Member')
        self.assertEqual(self.holder.password,original)
        self.assertFalse(self.holder.is_staff or self.holder.is_superuser)
        self.assertEqual(self.holder.email,'')
        self.assertEqual(MemberAccountControl.objects.get(user=self.holder).epoch,1)
        self.assertEqual(self.decide('cancelled',epoch=0).status_code,400)
        self.assertTrue(self.holder.is_active)

    def test_protected_accounts_csrf_confirmation_and_scoped_delegate(self):
        self.assertEqual(self.client.get(f'/operations/accounts/{self.admin.pk}/').status_code,404)
        with self.assertRaises(PermissionDenied):
            service.change_state(self.request,key=str(uuid.uuid4()),user_id=self.admin.pk,state='cancelled',expected_epoch=0,confirm=True)
        invalid=self.client.post(self.url,dict(action='suspended',key=str(uuid.uuid4()),expected_epoch=0))
        self.assertEqual(invalid.status_code,400)
        ids=[tag['id'] for tag in BeautifulSoup(invalid.content,'html.parser').select('[id]')]
        self.assertEqual(len(ids),len(set(ids)))
        csrf=Client(enforce_csrf_checks=True);csrf.cookies.update(self.client.cookies)
        self.assertEqual(csrf.post(self.url,{}).status_code,403)
        delegate=fixtures.synthetic_user('synthetic-account-delegate',True)
        row=Delegation.objects.create(user=delegate,capabilities=['account.view','account.suspend'])
        request=fixtures.administrative_request(delegate);request.session['authority_epoch']=row.epoch
        with self.assertRaises(PermissionDenied):
            service.change_state(request,key=str(uuid.uuid4()),user_id=self.holder.pk,state='cancelled',expected_epoch=0,confirm=True)
        service.change_state(request,key=str(uuid.uuid4()),user_id=self.holder.pk,state='suspended',expected_epoch=0,confirm=True)
        with self.assertRaises(PermissionDenied):
            service.change_state(self.request,key=str(uuid.uuid4()),user_id=delegate.pk,state='suspended',expected_epoch=0,confirm=True)

    def test_register_shows_distinct_account_membership_and_application_states(self):
        from . import services
        from django.utils import timezone
        call_command('seed_policy_prices',stdout=StringIO())
        self.person.verification_notice_at=timezone.now();self.person.save()
        app=services.create_application(self.person,'general')
        services.exempt_fee(self.request,key=str(uuid.uuid4()),application_id=app.pk,reason='Synthetic exemption')
        result=services.approve_membership(self.request,key=str(uuid.uuid4()),application_id=app.pk,reason='Synthetic approval')
        services.change_state(self.request,key=str(uuid.uuid4()),model='membership',object_id=result['membership'],state='cancelled',reason='Synthetic cancellation')
        response=self.client.get('/operations/membership/?lang=en')
        self.assertContains(response,'Application decision')
        self.assertContains(response,'Membership state')
        self.assertContains(response,'Login account state')
        self.assertContains(response,'Cancelled')
        self.assertContains(response,'Active')
        for lang in ('ar','fr','en'):
            self.assertEqual(self.client.get('/operations/accounts/?lang='+lang).status_code,200)
            self.assertEqual(self.client.get(self.url+'?lang='+lang).status_code,200)

    def test_edited_member_later_delegated_can_use_native_admin_login(self):
        from .delegation_cms import synchronize_cms_group
        old=Client();old.force_login(self.holder)
        service.edit_account(self.request,key=str(uuid.uuid4()),user_id=self.holder.pk,
            expected_epoch=0,confirm=True,fields=dict(username=self.holder.username,email='',
            first_name='',last_name='',full_name='Synthetic corrected',contact='',phone='',profession=''))
        self.holder.is_staff=True;self.holder.save(update_fields=['is_staff'])
        grant=Delegation.objects.create(user=self.holder,capabilities=['account.view'])
        synchronize_cms_group(self.holder,grant)
        fresh=Client()
        response=fresh.post('/admin/login/',{'username':self.holder.username,'password':'synthetic-password-123','next':'/admin/'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(fresh.session['member_account_epoch'],1)
        self.assertEqual(fresh.session['authority_epoch'],grant.epoch)
        self.assertEqual(fresh.get('/operations/accounts/').status_code,200)
        self.assertEqual(old.get('/operations/accounts/').status_code,302)
