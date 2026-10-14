"""Only synthetic private cases; no accreditation, payment or document creation."""
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from governance.models import Authority, Person, AccreditationCase
from governance.services import audit, encrypt, year_after

class Command(BaseCommand):
    help = 'Seed three synthetic independent assessment cases in owner-testing only.'
    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, 'ANTHEEC_OWNER_TESTING', False): raise CommandError('Owner-testing only')
        owner = Authority.objects.select_for_update().get(pk=1).primary
        if not owner.is_active: raise CommandError('Active owner required')
        made = 0
        for kind in ('individual', 'institution', 'course'):
            key = 'accreditation-v1-' + kind
            existing = AccreditationCase.objects.filter(fixture_key=key).first()
            if existing:
                if existing.kind != kind: raise CommandError('Fixture collision; rolled back')
                continue
            person = None
            subject = '[TEST ACCREDITATION V1] ' + kind
            if kind == 'individual':
                name = '[TEST ACCREDITATION V1] Individual'
                contact = 'accreditation-fixture-v1@example.invalid'
                if Person.objects.filter(contact=contact).exclude(full_name=name).exists():
                    raise CommandError('Fixture collision; rolled back')
                candidates = Person.objects.filter(contact=contact, full_name=name, user__isnull=True, guardian__isnull=True)
                if candidates.count() > 1: raise CommandError('Ambiguous fixture; rolled back')
                person = candidates.first() or Person.objects.create(full_name=name, contact=contact, verification_notice_at=timezone.now())
                subject = ''
            start = timezone.localdate()
            row = AccreditationCase.objects.create(fixture_key=key, kind=kind, person=person,
                subject_name=subject, starts_on=start, ends_on=year_after(start) if kind != 'course' else start + timedelta(days=7),
                private_payload=encrypt({'criteria':'Synthetic criteria for testing only; not organizational policy.',
                    'assessment':'Synthetic internal assessment; no accreditation granted.', 'fee':'', 'reason':'Synthetic owner-test fixture V1'}))
            audit(owner, 'testing.accreditation.case.created', row.pk)
            made += 1
        self.stdout.write(f'CREATED_TEST_ACCREDITATION_CASES: {made}')
