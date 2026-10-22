"""Apply the reviewed multilingual edition and public directory exactly once."""
import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Site
from content.models import EditorialPublication, InstitutionalPage, MultilingualPublication, PublicLeader

VERSION = 'multilingual-20261022-v1'
NAMES = [
    ('إدريس هلالي', 'Driss Helali', 'president'),
    ('فؤاد العلوي العماري', 'Fouad El Alaoui El Omari', 'vice_president'),
    ('مصلوحي سميرة', 'Maslouhi Samira', 'founder'),
    ('حنان المرنيسي', 'Hanane El Mernissi', 'founder'),
    ('سلمى بنوح', 'Salma Benouh', 'founder'),
    ('عبد السلام شنتوفي', 'Abdessalame Chentoufi', 'founder'),
    ('عبد الكبير علاوي', 'Abdelkbire Alaoui', 'founder'),
]


class Command(BaseCommand):
    help = 'Plan or publish the approved FR/EN translations and shared public leadership directory once.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        sites = list(Site.objects.select_for_update().filter(is_default_site=True))
        if len(sites) != 1:
            raise CommandError('Exactly one default site is required.')
        site = sites[0]
        directory = Path(__file__).resolve().parents[2]
        raw = {code: (directory / f'approved_{code}_20261022.json').read_bytes() for code in ('fr', 'en')}
        digest = hashlib.sha256(raw['fr'] + raw['en'] + json.dumps(NAMES, ensure_ascii=False).encode()).hexdigest()
        receipt = MultilingualPublication.objects.filter(site=site).first()
        if receipt:
            if receipt.version != VERSION or receipt.digest != digest:
                raise CommandError('Multilingual edition changed; review an edit-preserving update explicitly.')
            self.stdout.write('Multilingual edition already applied; all CMS and directory edits preserved.')
            return
        if not EditorialPublication.objects.filter(site=site, version='ar-20261022-v1').exists():
            raise CommandError('The approved Arabic edition must be published first.')
        home = InstitutionalPage.objects.select_for_update().get(pk=site.root_page_id)
        if home.locale.language_code != 'ar':
            raise CommandError('Expected the Arabic source home.')
        if PublicLeader.objects.filter(site=site).exists():
            raise CommandError('An existing directory requires explicit reconciliation; nothing overwritten.')
        editions = {code: json.loads(data) for code, data in raw.items()}
        sources = {'': home, **{p.slug: p.specific for p in home.get_children()}}
        expected = set(json.loads((directory / 'approved_ar_20261022.json').read_bytes())['pages'][i]['slug'] for i in range(17))
        if not expected.issubset(sources):
            raise CommandError('An Arabic source page is missing; reconcile before translating.')
        for slug in expected:
            source = sources[slug]
            if not source.live or source.get_view_restrictions().exists():
                raise CommandError('An Arabic source is unpublished or restricted; review before translating.')
        translated_homes = {}
        for code, edition in editions.items():
            if edition['version'] != VERSION or len(edition['pages']) != 17 or {e['slug'] for e in edition['pages']} != expected:
                raise CommandError('Unexpected multilingual payload.')
            local = home.get_translations().filter(locale__language_code=code).specific().first()
            if not local or not isinstance(local, InstitutionalPage) or not local.live:
                raise CommandError('Expected an existing published translated homepage.')
            local = InstitutionalPage.objects.select_for_update().get(pk=local.pk)
            if local.has_unpublished_changes:
                raise CommandError('Unpublished translated homepage changes require review.')
            if local.get_children().filter(slug__in=expected).exists():
                raise CommandError('A translated child already exists; nothing overwritten.')
            if any(sources[slug].get_translations().filter(locale=local.locale).exists() for slug in expected if slug):
                raise CommandError('An existing translation requires reconciliation.')
            translated_homes[code] = local
        if not options['apply']:
            self.stdout.write('PLAN: update two translated homes, create 32 linked translations and seven public directory entries; no changes made.')
            return
        if not getattr(settings, 'ANTHEEC_OPERATIONAL', False):
            raise CommandError('Applying the approved edition requires operational mode.')
        for code, edition in editions.items():
            local = translated_homes[code]
            entry = edition['pages'][0]
            leadership = [(b.block_type, b.value) for b in local.body if b.block_type == 'leadership']
            local.title = entry['title']
            local.seo_title = entry['seo_title']
            local.search_description = entry['search_description']
            local.editorial_home = True
            local.body = [(b['type'], b['value']) for b in entry['body']] + leadership
            local.save_revision(log_action=True).publish(log_action=True)
            for entry in edition['pages'][1:]:
                source = sources[entry['slug']]
                child = local.add_child(instance=InstitutionalPage(
                    title=entry['title'], slug=entry['slug'], locale=local.locale,
                    translation_key=source.translation_key, live=False, show_in_menus=True,
                    seo_title=entry['seo_title'], search_description=entry['search_description'],
                    body=[(b['type'], b['value']) for b in entry['body']]))
                child.save_revision(log_action=True).publish(log_action=True)
        for order, (ar, latin, role) in enumerate(NAMES):
            PublicLeader.objects.create(site=site, name_ar=ar, name_latin=latin, role=role,
                                        founder=True, published=True, sort_order=order)
        MultilingualPublication.objects.create(site=site, version=VERSION, digest=digest)
        self.stdout.write('Published FR/EN homes, 32 translations and shared public leadership. No accounts or documents created.')
