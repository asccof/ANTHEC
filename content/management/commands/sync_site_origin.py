"""Plan/apply the default CMS site's approved canonical origin without editing pages."""
from urllib.parse import urlsplit
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Site


class Command(BaseCommand):
    help = 'Align the single default Wagtail site with the configured HTTPS origin.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        origin = urlsplit(settings.ANTHEEC_PUBLIC_ORIGIN)
        if (origin.scheme != 'https' or not origin.hostname or origin.port is not None
                or origin.path not in {'', '/'} or origin.query or origin.fragment
                or origin.username or origin.password):
            raise CommandError('An exact HTTPS public origin is required.')
        sites = list(Site.objects.select_for_update().filter(is_default_site=True))
        if len(sites) != 1:
            raise CommandError('Exactly one default CMS site is required.')
        site = sites[0]
        if Site.objects.filter(hostname=origin.hostname, port=443).exclude(pk=site.pk).exists():
            raise CommandError('Another CMS site already uses this origin; review before changing it.')
        if not options['apply']:
            self.stdout.write('PLAN: align default CMS hostname/HTTPS port; no changes made.')
            return
        if not getattr(settings, 'ANTHEEC_OPERATIONAL', False):
            raise CommandError('Applying the origin requires the approved operational mode.')
        if site.hostname != origin.hostname or site.port != 443:
            site.hostname, site.port = origin.hostname, 443
            site.save(update_fields=['hostname', 'port'])
        self.stdout.write('Default CMS origin aligned; pages, members and issued assets preserved.')
