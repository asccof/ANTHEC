from django.core.management.base import BaseCommand
from governance.models import Outbox
from governance.documents import render_outbox


class Command(BaseCommand):
    help = "Render/retry encrypted synthetic printable documents locally; no delivery."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        count = 0
        for pk in (
            Outbox.objects.exclude(state__in=["rendered", "retired"])
            .order_by("attempts", "pk")
            .values_list("pk", flat=True)[: max(0, min(options["limit"], 1000))]
        ):
            render_outbox(pk)
            count += 1
        self.stdout.write(
            f"Processed {count} synthetic local document jobs; no external delivery."
        )
