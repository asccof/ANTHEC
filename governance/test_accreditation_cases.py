import uuid
from io import StringIO
from django.test import TestCase, Client, override_settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command, CommandError
from django.utils import timezone
from . import tests as fixtures, accreditation_services as service
from .services import decrypt, year_after
from .test_deployment import PRIVATE_MIDDLEWARE
from .models import Authority, Person, AccreditationCase, Accreditation, Document, Payment, Audit

class AccreditationCaseTests(TestCase):
    http_login = fixtures.PolicyTests.http_login
    def setUp(self):
        self.admin = fixtures.synthetic_user('synthetic-case-owner', True)
        Authority.objects.create(primary=self.admin)
        self.request = fixtures.administrative_request(self.admin)
        self.person = Person.objects.create(full_name='Synthetic Applicant', contact='case@example.invalid', verification_notice_at=timezone.now())
    def create(self, key=None, **changes):
        start = timezone.localdate()
        payload = dict(kind='individual', person_id=self.person.pk, subject_name='', starts_on=start.isoformat(), ends_on=year_after(start).isoformat(), criteria='PRIVATE-CRITERIA', assessment='PRIVATE-ASSESSMENT', fee='125.00', reason='PRIVATE-REASON')
        payload.update(changes)
        return service.create(self.request, key=key or str(uuid.uuid4()), **payload)['case']
    def review(self, pk, decision='reviewed', key=None, **changes):
        payload=dict(case_id=pk, decision=decision, criteria='PRIVATE-CRITERIA', assessment='PRIVATE-ASSESSMENT', fee='125.00', reason='PRIVATE-REASON')
        payload.update(changes)
        return service.review(self.request,key=key or str(uuid.uuid4()),**payload)
    def test_encryption_audit_minimization_and_replay(self):
        key=str(uuid.uuid4()); pk=self.create(key)
        self.assertEqual(self.create(key),pk)
        row=AccreditationCase.objects.get(pk=pk)
        self.assertNotIn('PRIVATE',row.private_payload)
        self.assertEqual(decrypt(row.private_payload)['fee'],'125.00')
        key=str(uuid.uuid4()); result=self.review(pk,key=key)
        self.assertEqual(self.review(pk,key=key),result)
        audit=str(list(Audit.objects.values('reason','details')))
        for value in ('PRIVATE-CRITERIA','PRIVATE-ASSESSMENT','PRIVATE-REASON','125.00'):
            self.assertNotIn(value,audit)
    def test_subject_dates_fee_and_complete_assessment_validation(self):
        for changes in ({'kind':'professional'}, {'kind':'institution'}, {'subject_name':'Unexpected'}, {'ends_on':timezone.localdate().isoformat()}, {'fee':'NaN'}, {'fee':'-1'}, {'fee':'1.001'}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError): self.create(**changes)
        self.assertEqual(AccreditationCase.objects.count(),0)
        self.person.verification_notice_at=None; self.person.save()
        with self.assertRaises(ValidationError): self.create()
        pk=self.create(kind='course',person_id=None,subject_name='Synthetic Course')
        with self.assertRaises(ValidationError): self.review(pk,assessment='')
        self.assertEqual(AccreditationCase.objects.get(pk=pk).state,'draft')
    def test_rejection_is_terminal_and_creates_no_right_or_document(self):
        pk=self.create(); self.review(pk,'rejected')
        with self.assertRaises(ValidationError): self.review(pk)
        with self.assertRaises(ValidationError): service.approve(self.request,key=str(uuid.uuid4()),case_id=pk,reason='Synthetic')
        self.assertEqual(Accreditation.objects.count(),0)
        self.assertEqual(Document.objects.count(),0); self.assertEqual(Payment.objects.count(),0)
    @override_settings(ANTHEEC_OWNER_TESTING=True,MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_owner_testing_blocks_issuance_even_forged_post(self):
        pk=self.create(); self.review(pk)
        with self.assertRaises(PermissionDenied): service.approve(self.request,key=str(uuid.uuid4()),case_id=pk,reason='Synthetic')
        self.http_login()
        response=self.client.post(f'/operations/accreditation/{pk}/',{'operation':'approve','key':str(uuid.uuid4()),'reason':'Synthetic'})
        self.assertEqual(response.status_code,403)
        self.assertEqual(AccreditationCase.objects.get(pk=pk).state,'reviewed')
        self.assertEqual(Accreditation.objects.count(),0); self.assertEqual(Document.objects.count(),0)
    @override_settings(ANTHEEC_OWNER_TESTING=True,MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_access_localization_csrf_and_recent_mfa(self):
        pk=self.create()
        self.assertEqual(self.client.get(f'/operations/accreditation/{pk}/').status_code,404)
        self.http_login()
        for lang in ('ar','fr','en'):
            response=self.client.get(f'/operations/accreditation/{pk}/?lang={lang}')
            self.assertContains(response,'PRIVATE-CRITERIA')
            self.assertIn('no-store',response['Cache-Control'])
        outsider=fixtures.synthetic_user('synthetic-case-outsider',True)
        self.http_login(user=outsider)
        self.assertEqual(self.client.get(f'/operations/accreditation/{pk}/').status_code,404)
        self.http_login()
        csrf=Client(enforce_csrf_checks=True); self.http_login(client=csrf)
        self.assertEqual(csrf.post('/operations/accreditation/',{}).status_code,403)
        self.request.session["authority_epoch"] = -1
        with self.assertRaises(PermissionDenied): self.review(pk)
    def test_seed_guard_and_idempotency(self):
        with self.assertRaises(CommandError): call_command('seed_accreditation_demo',stdout=StringIO())
        with override_settings(ANTHEEC_OWNER_TESTING=True):
            call_command('seed_accreditation_demo',stdout=StringIO())
            call_command('seed_accreditation_demo',stdout=StringIO())
        self.assertEqual(AccreditationCase.objects.count(),3)
        self.assertEqual(Accreditation.objects.count(),0); self.assertEqual(Document.objects.count(),0)

    def test_approval_reuses_issuance_and_is_replay_safe(self):
        pk=self.create(); self.review(pk)
        key=str(uuid.uuid4())
        result=service.approve(self.request,key=key,case_id=pk,reason='PRIVATE-APPROVAL-REASON')
        self.assertEqual(service.approve(self.request,key=key,case_id=pk,reason='PRIVATE-APPROVAL-REASON'),result)
        row=AccreditationCase.objects.get(pk=pk)
        self.assertEqual(row.state,'approved')
        self.assertEqual(row.accreditation_id,result['accreditation'])
        self.assertIsNone(row.accreditation.membership_id)
        self.assertEqual(Document.objects.count(),1)
        self.assertNotIn('PRIVATE-APPROVAL-REASON',str(list(Audit.objects.values('reason','details'))))
        final=Audit.objects.get(action='accreditation.case.approved')
        self.assertEqual(decrypt(final.details['private_payload'])['reason'],'PRIVATE-APPROVAL-REASON')
        with self.assertRaises(ValidationError): self.review(pk)
        with self.assertRaises(ValidationError): service.approve(self.request,key=str(uuid.uuid4()),case_id=pk,reason='Synthetic')

    def test_issuance_failure_rolls_back_case_and_right(self):
        from unittest.mock import patch
        pk=self.create(); self.review(pk)
        with patch('governance.services.issue',side_effect=ValidationError('Synthetic issue failure')):
            with self.assertRaises(ValidationError): service.approve(self.request,key=str(uuid.uuid4()),case_id=pk,reason='Synthetic')
        row=AccreditationCase.objects.get(pk=pk)
        self.assertEqual(row.state,'reviewed'); self.assertIsNone(row.accreditation_id)
        self.assertEqual(Accreditation.objects.count(),0)

    @override_settings(ANTHEEC_OWNER_TESTING=True,MIDDLEWARE=PRIVATE_MIDDLEWARE)
    def test_http_create_review_and_encrypted_history(self):
        self.http_login()
        start=timezone.localdate()
        response=self.client.post('/operations/accreditation/?lang=fr',dict(key=str(uuid.uuid4()),kind='institution',person='',subject='Synthetic Institution',start=start.isoformat(),end=year_after(start).isoformat(),criteria='PRIVATE-CRITERIA',assessment='',fee='',reason='PRIVATE-CREATE'))
        self.assertEqual(response.status_code,302)
        pk=AccreditationCase.objects.get().pk
        url=f'/operations/accreditation/{pk}/?lang=fr'
        response=self.client.post(url,dict(key=str(uuid.uuid4()),decision='reviewed',criteria='PRIVATE-CRITERIA',assessment='PRIVATE-ASSESSMENT',fee='0.00',reason='PRIVATE-REVIEW'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(AccreditationCase.objects.get(pk=pk).state,'reviewed')
        response=self.client.get(url)
        self.assertContains(response,'PRIVATE-CREATE'); self.assertContains(response,'PRIVATE-REVIEW')
        for event in Audit.objects.filter(action__startswith='accreditation.case.'):
            self.assertNotIn('PRIVATE',str(event.details))
        response=self.client.post(url,dict(key=str(uuid.uuid4()),decision='rejected',criteria='PRIVATE-CRITERIA',assessment='PRIVATE-ASSESSMENT',fee='',reason='PRIVATE-REJECT'))
        self.assertEqual(response.status_code,302)
        self.assertEqual(AccreditationCase.objects.get(pk=pk).state,'rejected')
        self.assertEqual(Document.objects.count(),0)
