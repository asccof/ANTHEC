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
        return context
