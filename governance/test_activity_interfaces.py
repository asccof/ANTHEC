import uuid
from io import StringIO
from datetime import timedelta
from django.test import TestCase,Client,override_settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command,CommandError
from django.utils import timezone
from . import tests as fixtures,services,activity_services
from .models import Authority,Activity,Person,Registration,Document,Attendance
from .test_deployment import PRIVATE_MIDDLEWARE

class ActivityInterfaceTests(TestCase):
    http_login=fixtures.PolicyTests.http_login
    def setUp(self):
        self.admin=fixtures.synthetic_user('synthetic-activity-owner',True)
        Authority.objects.create(primary=self.admin)
        self.request=fixtures.administrative_request(self.admin)
        self.holder=fixtures.synthetic_user('synthetic-activity-holder')
        self.other=fixtures.synthetic_user('synthetic-activity-other')
        self.person=Person.objects.create(user=self.holder,full_name='Synthetic Adult',contact='adult@example.invalid',verification_notice_at=timezone.now())
        self.minor=Person.objects.create(guardian=self.holder,minor=True,full_name='Synthetic Minor',contact='minor@example.invalid',verification_notice_at=timezone.now())
        today=timezone.localdate()
        self.activity=Activity.objects.create(title='Synthetic Activity',starts_on=today,ends_on=today+timedelta(days=1),capacity=2,allows_minors=True,consent_version='synthetic-v1',consent_text='SYNTHETIC-CONSENT')
    def payload(self,**changes):
        data=dict(title=self.activity.title,starts_on=self.activity.starts_on.isoformat(),ends_on=self.activity.ends_on.isoformat(),capacity=2,allows_minors=True,consent_version='synthetic-v1',consent_text='SYNTHETIC-CONSENT',reason='Synthetic configuration')
        data.update(changes);return data
    def registration(self,minor=False):
        return services.register(self.activity,self.minor if minor else self.person,self.holder,guardian_name='Synthetic Guardian' if minor else '',guardian_capacity='Synthetic legal guardian' if minor else '',consent=minor)
    def test_configuration_validation_and_replay(self):
        key=str(uuid.uuid4());data=self.payload()
        result=activity_services.create(self.request,key=key,**data)
        self.assertEqual(activity_services.create(self.request,key=key,**data),result)
        for change in ({'capacity':0},{'capacity':True},{'ends_on':'2000-01-01'},{'consent_text':''},{'allows_minors':'yes'}):
            with self.subTest(change=change),self.assertRaises(ValidationError):activity_services.create(self.request,key=str(uuid.uuid4()),**self.payload(**change))
    def test_existing_conditions_frozen_and_capacity_respects_confirmed(self):
        row=self.registration()
        for change in ({'consent_text':'Changed'},{'starts_on':'2000-01-01'},{'allows_minors':False}):
            with self.assertRaises(ValidationError):activity_services.update(self.request,key=str(uuid.uuid4()),activity_id=self.activity.pk,**self.payload(**change))
        activity_services.update(self.request,key=str(uuid.uuid4()),activity_id=self.activity.pk,**self.payload(title='Revised',capacity=1))
        services.decide_registration(self.request,key=str(uuid.uuid4()),registration_id=row.pk,accept=True,reason='Synthetic acceptance')
        second=self.registration(minor=True)
        # Existing admission command keeps the capacity limit.
        with self.assertRaises(ValidationError):services.decide_registration(self.request,key=str(uuid.uuid4()),registration_id=second.pk,accept=True,reason='Synthetic')
    def test_participant_scope_and_minor_consent_http(self):
        self.client.force_login(self.holder)
        url=f'/activities/{self.activity.pk}/?lang=en'
        response=self.client.get(url)
        self.assertContains(response,'Synthetic Adult');self.assertContains(response,'Synthetic Minor')
        self.assertContains(response,'SYNTHETIC-CONSENT')
        foreign=Person.objects.create(user=self.other,full_name='PRIVATE-OTHER',verification_notice_at=timezone.now())
        response=self.client.get(url);self.assertNotContains(response,'PRIVATE-OTHER')
        self.assertEqual(self.client.post(url,{'person':foreign.pk}).status_code,400)
        self.assertEqual(self.client.post(url,{'person':self.minor.pk,'guardian_name':'Synthetic Guardian','guardian_capacity':'Synthetic legal guardian'}).status_code,400)
        response=self.client.post(url,{'person':self.minor.pk,'guardian_name':'Synthetic Guardian','guardian_capacity':'Synthetic legal guardian','consent':True})
        self.assertEqual(response.status_code,302)
        row=Registration.objects.get()
        self.assertEqual(row.consent_text,'SYNTHETIC-CONSENT');self.assertEqual(row.consent_version,'synthetic-v1')
        self.assertEqual(self.client.post(url,{'person':self.minor.pk,'guardian_name':'Synthetic Guardian','guardian_capacity':'Synthetic legal guardian','consent':True}).status_code,400)
        self.assertEqual(Registration.objects.count(),1)
    def test_new_registrations_use_locked_current_conditions(self):
        stale=self.activity
        Activity.objects.filter(pk=stale.pk).update(allows_minors=False)
        with self.assertRaises(ValidationError):services.register(stale,self.minor,self.holder,guardian_name='Synthetic Guardian',guardian_capacity='Synthetic legal guardian',consent=True)
        self.assertEqual(Registration.objects.count(),0)
    def test_administrative_decision_and_attendance_interfaces(self):
        row=self.registration();self.http_login()
        url=f'/operations/activities/registrations/{row.pk}/?lang=en'
        response=self.client.post(url,{'operation':'accept','key':str(uuid.uuid4()),'reason':'Synthetic acceptance'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Document.objects.count(),1)
        key=str(uuid.uuid4());data={'operation':'checkin','key':key}
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(Attendance.objects.count(),1)
        self.assertContains(self.client.get(url),'Present')
        self.assertEqual(self.client.post(url,{'operation':'cancel','key':str(uuid.uuid4()),'reason':'Synthetic cancellation'}).status_code,302)
        self.assertEqual(self.client.post(url,{'operation':'checkin','key':str(uuid.uuid4())}).status_code,400)
    @override_settings(ANTHEEC_OWNER_TESTING=True,MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_owner_guards_locales_and_forged_acceptance(self):
        row=Registration.objects.create(activity=self.activity,person=self.person,submitted_by=self.holder)
        self.assertEqual(self.client.get('/operations/activities/').status_code,404)
        self.http_login()
        for lang in ('ar','fr','en'):
            response=self.client.get('/operations/activities/?lang='+lang)
            self.assertEqual(response.status_code,200);self.assertIn('no-store',response['Cache-Control'])
        preview=self.client.get(f'/activities/{self.activity.pk}/')
        self.assertContains(preview,'fieldset disabled')
        self.assertEqual(self.client.post(f'/activities/{self.activity.pk}/',{'person':self.person.pk}).status_code,403)
        url=f'/operations/activities/registrations/{row.pk}/'
        self.assertEqual(self.client.post(url,{'operation':'accept','key':str(uuid.uuid4()),'reason':'Synthetic'}).status_code,403)
        self.assertEqual(Document.objects.count(),0)
        self.assertEqual(self.client.post(url,{'operation':'reject','key':str(uuid.uuid4()),'reason':'Synthetic rejection'}).status_code,302)
        self.assertEqual(Registration.objects.get(pk=row.pk).state,'rejected')
    def test_admin_authority_csrf_and_recent_mfa(self):
        self.http_login(user=self.holder)
        self.assertEqual(self.client.get('/operations/activities/').status_code,403)
        csrf=Client(enforce_csrf_checks=True);self.http_login(client=csrf)
        self.assertEqual(csrf.post('/operations/activities/',{}).status_code,403)
        self.request.session['reauth_at']=0
        with self.assertRaises(PermissionDenied):activity_services.create(self.request,key=str(uuid.uuid4()),**self.payload())
    def test_manual_fixture_guard_idempotency_and_no_documents(self):
        with self.assertRaises(CommandError):call_command('seed_activity_demo',stdout=StringIO())
        with override_settings(ANTHEEC_OWNER_TESTING=True):
            call_command('seed_activity_demo',stdout=StringIO())
            call_command('seed_activity_demo',stdout=StringIO())
        self.assertEqual(Activity.objects.filter(fixture_key__isnull=False).count(),2)
        self.assertEqual(Registration.objects.count(),2)
        self.assertEqual(Document.objects.count(),0)
        from django.contrib.auth import get_user_model
        self.assertFalse(get_user_model().objects.get(username='synthetic-activity-participant-v1').has_usable_password())
    def test_member_listing_has_no_other_participant_disclosure(self):
        row=self.registration();self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/activities/'),'Synthetic Adult')
        self.assertEqual(self.client.get(f'/operations/activities/registrations/{row.pk}/').status_code,403)
