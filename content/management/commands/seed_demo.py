from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Locale, Page, Site
from content.models import InstitutionalPage


class Command(BaseCommand):
    help = "Seed only synthetic multilingual public CMS content; no people or credentials."

    @transaction.atomic
    def handle(self, *args, **options):
        locales = {code: Locale.objects.get_or_create(language_code=code)[0] for code in ("ar", "fr", "en")}
        root = Page.get_first_root_node()
        site = Site.objects.filter(is_default_site=True).first()
        if site and isinstance(site.root_page.specific, InstitutionalPage):
            self.stdout.write("Synthetic CMS already exists; no changes made.")
            return
        if site:
            current = site.root_page.specific
            fresh_placeholder = (
                type(current) is Page
                and current.title == "Welcome to your new Wagtail site!"
                and current.slug == "home"
                and current.depth == 2
                and current.get_parent().pk == root.pk
                and Page.objects.count() == 2
                and not current.revisions.exists()
                and not current.seo_title
                and not current.search_description
                and site.hostname == "localhost"
                and site.port == 80
            )
            if not fresh_placeholder:
                raise CommandError("Refusing to replace an existing site; seed requires a fresh Wagtail placeholder.")
        data = {
            "ar": ("منصة ANTHEEC التجريبية", "مرحلة التطوير", "هذه صفحة تطوير اصطناعية. مسارات العضوية متاحة لاختبار بيانات اصطناعية فقط؛ لا ترسل بيانات أشخاص حقيقيين."),
            "fr": ("Plateforme de démonstration ANTHEEC", "Développement en cours", "Page de développement fictive. Les parcours d’adhésion utilisent uniquement des données fictives ; aucune donnée réelle."),
            "en": ("ANTHEEC demonstration platform", "Development in progress", "Synthetic development page. Membership workflows support synthetic data only; do not submit real-person data."),
        }
        title, heading, text = data["ar"]
        home = root.add_child(instance=InstitutionalPage(title=title, slug="antheec-demo", locale=locales["ar"], live=False, body=[("heading", heading), ("paragraph", text)]))
        home.save_revision().publish()
        for code in ("fr", "en"):
            translated = home.copy_for_translation(locales[code])
            translated.title, heading, text = data[code]
            translated.body = [("heading", heading), ("paragraph", text)]
            translated.save_revision().publish()
        if site:
            site.root_page = home
            site.hostname = "localhost"
            site.port = 8000
            site.save()
        else:
            Site.objects.create(hostname="localhost", port=8000, root_page=home, is_default_site=True, site_name="ANTHEEC demo")
        self.stdout.write("Synthetic AR/FR/EN content created. No user or delivery created.")
