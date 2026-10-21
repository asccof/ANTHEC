from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class InstitutionalPage(Page):
    """Editable structured content; all fields are public content, never applicant data."""
    body = StreamField([
        ("heading", blocks.CharBlock()),
        ("paragraph", blocks.TextBlock()),
        ("leadership", blocks.StructBlock([
            ("role", blocks.ChoiceBlock(choices=[("president", "President"), ("vice_president", "Vice-president"), ("founding_council", "Founding council member")])),
            ("name", blocks.CharBlock(max_length=200)),
        ], label="Public leadership — approved names only")),
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
        context["synthetic_preview"] = not context["owner_testing"] and not getattr(settings, "ANTHEEC_OPERATIONAL", False)
        site = Site.find_for_request(request)
        context["is_site_home"] = bool(site and site.root_page.translation_key == self.translation_key)
        if site:
            home = Page.objects.live().public().filter(
                translation_key=site.root_page.translation_key, locale=self.locale).first()
            context["localized_home_url"] = home.url if home else None
        # Read-only public requests must not create configuration rows.
        contact = PublicContact.objects.filter(site=site).first() if site else None
        context["public_contact"] = (contact or PublicContact()).public_values(language)
        if context["is_site_home"]:
            context["membership_prices"] = current_memberships(language)
            labels = context["public_labels"]
            context["leadership_groups"] = [dict(role=role, label=labels[role], names=[block.value["name"] for block in self.body if block.block_type == "leadership" and block.value["role"] == role]) for role in ("president", "vice_president", "founding_council")]
        return context


from django.db import models
from django.core.validators import RegexValidator
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_setting(icon="mail")
class PublicContact(BaseSiteSetting):
    """Owner-approved public association contacts; never account contact fields."""
    phone = models.CharField("الهاتف وواتساب / Phone and WhatsApp", max_length=16, blank=True,
        default="0663400190", validators=[RegexValidator(r"^(?:0[0-9]{9}|\+[1-9][0-9]{6,14})\Z", "Use a Moroccan 10-digit number or +international format.")])
    address_ar = models.CharField("العنوان بالعربية / Arabic address", max_length=500, blank=True, default="رقم 43، زنقة أكلمام سيدي علي، أكدال، الرباط")
    address_fr = models.CharField("العنوان بالفرنسية / French address", max_length=500, blank=True, default="43, rue Aguelmam Sidi Ali, Agdal, Rabat")
    address_en = models.CharField("العنوان بالإنجليزية / English address", max_length=500, blank=True, default="43, Aguelmam Sidi Ali Street, Agdal, Rabat")
    email = models.EmailField("البريد الرسمي للجمعية / Official association email", blank=True, default="")
    panels = [FieldPanel("phone"), FieldPanel("address_ar"), FieldPanel("address_fr"), FieldPanel("address_en"), FieldPanel("email")]

    class Meta:
        verbose_name = "بيانات التواصل / Public contact"

    def public_values(self, language):
        from django.core.exceptions import ValidationError
        phone = self.phone
        try:
            self._meta.get_field("phone").clean(phone, self)
        except ValidationError:
            phone = ""
        number = ("212" + phone[1:]) if phone.startswith("0") else phone.lstrip("+")
        email = self.email
        try:
            self._meta.get_field("email").clean(email, self)
        except ValidationError:
            email = ""
        from urllib.parse import quote
        return dict(mailto="mailto:" + quote(email, safe="@") if email else "", phone=phone, tel="+" + number if number else "", whatsapp="https://wa.me/" + number if number else "", email=email,
            address=getattr(self, "address_" + (language if language in ("ar", "fr", "en") else "ar")))
