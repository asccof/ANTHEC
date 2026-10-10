from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from governance.models import Authority, Audit


class Command(BaseCommand):
    help = "Initialize exactly one primary director from an existing synthetic account; no replacement allowed."

    def add_arguments(self, parser):
        parser.add_argument("username")

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.get(username=options["username"])
        if not user.email.endswith("@example.invalid") or not user.is_active:
            raise CommandError(
                "Synthetic active account with example.invalid address required"
            )
        if Authority.objects.exists():
            raise CommandError(
                "Authority already initialized; replacement is forbidden"
            )
        if not user.is_superuser:
            raise CommandError("Use the designated synthetic primary superuser")
        Authority.objects.create(primary=user)
        Audit.objects.create(
            actor=user, action="authority.bootstrapped", subject=str(user.pk)
        )
        self.stdout.write(
            "Primary authority initialized. Enroll MFA before administrative access."
        )
