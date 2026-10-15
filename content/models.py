from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class InstitutionalPage(Page):
    """Editable structured content; all fields are public content, never applicant data."""
    body = StreamField([
        ("heading", blocks.CharBlock()),
        ("paragraph", blocks.TextBlock()),
    ], blank=True, use_json_field=True)
    content_panels = Page.content_panels + [FieldPanel("body")]
    template = "content/institutional_page.html"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["language_versions"] = self.get_translations(inclusive=True).live().public().order_by("locale__language_code")
        from django.conf import settings
        from wagtail.models import Site
        from .presentation import vocabulary, current_memberships
        language = self.locale.language_code
        context["public_labels"] = vocabulary(language)
        context["owner_testing"] = getattr(settings, "ANTHEEC_OWNER_TESTING", False)
        site = Site.find_for_request(request)
        context["is_site_home"] = bool(site and site.root_page.translation_key == self.translation_key)
        if site:
            home = Page.objects.live().public().filter(
                translation_key=site.root_page.translation_key, locale=self.locale).first()
            context["localized_home_url"] = home.url if home else None
        if context["is_site_home"]:
            context["membership_prices"] = current_memberships(language)
        return context
