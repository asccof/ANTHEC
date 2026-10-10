from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from governance.models import Price
from governance.services import TIERS


class Command(BaseCommand):
    help = "Seed owner-approved initial prices idempotently, without resetting administrative edits."

    @transaction.atomic
    def handle(self, *args, **options):
        for tier, amount in TIERS.items():
            if not Price.objects.filter(tier=tier).exists():
                Price.objects.create(
                    tier=tier,
                    amount=amount,
                    starts_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
                )
        self.stdout.write("Approved initial price versions ready.")
