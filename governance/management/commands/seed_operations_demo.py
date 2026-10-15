"""One synthetic unprivileged candidate; no delegation, prices or credentials."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from governance.models import Authority
from governance.services import audit

class Command(BaseCommand):
    help = "Create an unusable-password synthetic director candidate in owner-testing only."
    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "ANTHEEC_OWNER_TESTING", False):
            raise CommandError("Owner-testing only")
        owner = Authority.objects.select_for_update().get(pk=1).primary
        if not owner.is_active:
            raise CommandError("Active owner required")
        user, created = get_user_model().objects.get_or_create(
            username="synthetic-director-candidate-v1",
            defaults={"email": "director-candidate-v1@example.invalid"})
        if not created and (user.email != "director-candidate-v1@example.invalid" or user.is_superuser or user.is_staff or user.has_usable_password()):
            raise CommandError("Fixture collision; transaction rolled back")
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            audit(owner, "testing.director.candidate.created", user.pk)
        self.stdout.write("CREATED_TEST_DIRECTOR_CANDIDATES: " + str(int(created)))
