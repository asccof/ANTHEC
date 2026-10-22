"""Owner-approved public Arabic copy, imported once without overwriting future CMS edits."""
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Page, Site
from content.models import EditorialPublication, InstitutionalPage

VERSION = 'ar-20261022-v1'

class Command(BaseCommand):
    help = 'Plan or apply the approved Arabic CMS edition once; does not touch member data.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        sites = list(Site.objects.select_for_update().filter(is_default_site=True))
        if len(sites) != 1:
            raise CommandError('Exactly one default site is required.')
        site = sites[0]
        receipt = EditorialPublication.objects.filter(site=site).first()
        if receipt:
            if receipt.version != VERSION:
                raise CommandError('Another editorial edition was already applied; review explicitly.')
            self.stdout.write('Approved Arabic edition already applied; CMS edits preserved.')
            return
        Page.objects.select_for_update().get(pk=site.root_page_id)
        home = site.root_page.specific
        if isinstance(home, InstitutionalPage):
            home = InstitutionalPage.objects.select_for_update().get(pk=home.pk)
        if not isinstance(home, InstitutionalPage) or home.locale.language_code != 'ar':
            raise CommandError('Expected the existing Arabic institutional site root.')
        if home.has_unpublished_changes:
            raise CommandError('Unpublished homepage changes exist; review before import.')
        raw = (Path(__file__).resolve().parents[2] / 'approved_ar_20261022.json').read_bytes()
        edition = json.loads(raw)
        if edition['version'] != VERSION or len(edition['pages']) != 17:
            raise CommandError('Unexpected editorial payload.')
        slugs = [entry['slug'] for entry in edition['pages'][1:]]
        if home.get_children().filter(slug__in=slugs).exists():
            raise CommandError('An approved slug already exists; no pages were overwritten.')
        if not options['apply']:
            self.stdout.write('PLAN: update one Arabic homepage and create 16 published Arabic pages; no changes made.')
            return
        if not getattr(settings, 'ANTHEEC_OPERATIONAL', False):
            raise CommandError('Applying approved copy requires the authorized operational mode.')
        leadership = [(b.block_type, b.value) for b in home.body if b.block_type == 'leadership']
        entry = edition['pages'][0]
        home.title = 'الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ'
        home.seo_title = 'ANTHEC | الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ'
        home.search_description = entry['search_description']
        home.body = [(b['type'], b['value']) for b in entry['body']] + leadership
        home.editorial_home = True
        home.save_revision(log_action=True).publish(log_action=True)
        for entry in edition['pages'][1:]:
            child = home.add_child(instance=InstitutionalPage(
                title=entry['title'], slug=entry['slug'], locale=home.locale, live=False,
                show_in_menus=True, seo_title=entry['seo_title'],
                search_description=entry['search_description'],
                body=[(b['type'], b['value']) for b in entry['body']]))
            child.save_revision(log_action=True).publish(log_action=True)
        EditorialPublication.objects.create(site=site, version=VERSION, digest=hashlib.sha256(raw).hexdigest())
        self.stdout.write('Published approved Arabic homepage and 16 pages; future CMS edits will not be reimported.')
