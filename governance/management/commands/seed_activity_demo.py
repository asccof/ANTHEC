"""Idempotent synthetic activity/participation fixtures, never invitations."""
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from governance.models import Authority, Activity, Person, Registration
from governance.services import audit

class Command(BaseCommand):
    help='Seed synthetic adult/guardian participation cases in owner-testing only.'
    @transaction.atomic
    def handle(self,*args,**options):
        if not getattr(settings,'ANTHEEC_OWNER_TESTING',False):raise CommandError('Owner-testing only')
        owner=Authority.objects.select_for_update().get(pk=1).primary
        if not owner.is_active:raise CommandError('Active owner required')
        username='synthetic-activity-participant-v1'
        user,created=get_user_model().objects.get_or_create(username=username,defaults={'email':'activity-participant-v1@example.invalid'})
        if not created and (user.email!='activity-participant-v1@example.invalid' or user.is_staff or user.is_superuser or user.has_usable_password()):
            raise CommandError('Fixture account collision; rolled back')
        if created:user.set_unusable_password();user.save(update_fields=['password'])
        start=timezone.localdate();made=0
        for minor in (False,True):
            suffix='minor' if minor else 'adult'
            contact=f'activity-fixture-v1-{suffix}@example.invalid'
            name='[TEST ACTIVITY V1] '+suffix
            candidates=Person.objects.filter(contact=contact)
            if candidates.count()>1:raise CommandError('Ambiguous fixture; rolled back')
            person=candidates.first()
            if person and (person.full_name!=name or person.minor!=minor or person.guardian_id!=(owner.pk if minor else None) or person.user_id!=(None if minor else user.pk)):
                raise CommandError('Fixture profile collision; rolled back')
            if not person:
                person=Person.objects.create(full_name=name,contact=contact,minor=minor,user=None if minor else user,guardian=owner if minor else None,verification_notice_at=timezone.now())
            key='activity-v1-'+suffix
            activity,created=Activity.objects.get_or_create(fixture_key=key,defaults={'title':name,'starts_on':start,'ends_on':start+timedelta(days=7),'capacity':5,'allows_minors':minor,'consent_version':'synthetic-v1','consent_text':'Synthetic guardian consent for private testing only; not a legal template.' if minor else ''})
            if activity.title!=name or activity.allows_minors!=minor:raise CommandError('Activity fixture collision; rolled back')
            row,created=Registration.objects.get_or_create(activity=activity,person=person,defaults={'submitted_by':owner if minor else user,'guardian_name':'[TEST] Guardian' if minor else '', 'guardian_capacity':'[TEST] Legal representative' if minor else '', 'consent_at':timezone.now() if minor else None,'consent_version':activity.consent_version if minor else '', 'consent_text':activity.consent_text if minor else ''})
            if created:audit(owner,'testing.registration.created',row.pk);made+=1
        self.stdout.write(f'CREATED_TEST_ACTIVITY_REQUESTS: {made}')
