"""Small, idempotent fixtures; no publication, approval, credentials or delivery."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from governance.models import Authority, PartnershipRequest
from governance.services import audit

class Command(BaseCommand):
    help='Seed three explicitly synthetic pending partnership requests in owner-testing only.'
    @transaction.atomic
    def handle(self,*args,**options):
        if not getattr(settings,'ANTHEEC_OWNER_TESTING',False): raise CommandError('Owner-testing only')
        owner=Authority.objects.select_for_update().get(pk=1).primary
        if not owner.is_active: raise CommandError('Active owner required')
        made=0
        for number in range(1,4):
            name=f'[TEST PARTNER V1] Organization {number}'
            email=f'partner-fixture-{number}@example.invalid'
            row,created=PartnershipRequest.objects.get_or_create(fixture_key=f'partner-v1-{number}',defaults={'organization':name,'contact_email':email,'message':'Synthetic partnership proposal for private testing only.','notice_acknowledged':True})
            if row.organization!=name or row.contact_email!=email: raise CommandError('Fixture collision; transaction rolled back')
            if created:
                audit(owner,'testing.partnership.created',row.pk,reason='Synthetic owner-test fixture V1')
                made+=1
        self.stdout.write(f'CREATED_TEST_PARTNERSHIP_REQUESTS: {made}')
