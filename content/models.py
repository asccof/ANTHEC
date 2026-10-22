from django.db import models
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
    editorial_home = models.BooleanField(
        "عرض محتوى الرئيسية من محرر الصفحات / Editable homepage", default=False, db_default=False)
    content_panels = Page.content_panels + [FieldPanel("editorial_home"), FieldPanel("body")]
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
        context["editorial_navigation"] = []
        if site:
            local_home = Page.objects.live().public().filter(
                translation_key=site.root_page.translation_key, locale=self.locale).specific().first()
            if local_home:
                context["editorial_navigation"] = local_home.get_children().live().public().in_menu().filter(locale=self.locale)
        from .navigation import navigation_groups
        context["navigation_groups"] = navigation_groups(context["editorial_navigation"], language)
        context["public_leadership"] = [person.public_values(language) for person in PublicLeader.objects.filter(site=site, published=True)] if site else []
        context["directory_configured"] = bool(site and MultilingualPublication.objects.filter(site=site).exists())
        context["is_structure_page"] = self.slug == "governance"
        if context["is_site_home"] and self.editorial_home:
            content = [block for block in self.body if block.block_type != "leadership"]
            context["editorial_hero"] = content[0].value if content and content[0].block_type == "heading" else self.title
            context["editorial_hero_lines"] = context["editorial_hero"].split(". ")
            context["editorial_intro"] = content[1].value if len(content) > 1 and content[1].block_type == "paragraph" else ""
            context["editorial_body"] = content[2:] if context["editorial_intro"] else content
            sections = []
            for block in context["editorial_body"]:
                if block.block_type == "heading":
                    sections.append({"heading": block.value, "paragraphs": []})
                elif block.block_type == "paragraph":
                    if not sections:
                        sections.append({"heading": "", "paragraphs": []})
                    sections[-1]["paragraphs"].append(block.value)
            context["home_sections"] = sections
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


class EditorialPublication(models.Model):
    """One-time import receipt outside page revisions: subsequent edits stay authoritative."""
    site = models.OneToOneField("wagtailcore.Site", on_delete=models.PROTECT)
    version = models.CharField(max_length=40)
    digest = models.CharField(max_length=64)
    applied_at = models.DateTimeField(auto_now_add=True)


class PublicLeader(models.Model):
    """Public directory only; editing never creates accounts, cards or authority."""
    site = models.ForeignKey("wagtailcore.Site", on_delete=models.PROTECT)
    name_ar = models.CharField("الاسم بالعربية / Arabic name", max_length=200)
    name_latin = models.CharField("الاسم بالحروف اللاتينية / Latin-script name", max_length=200)
    role = models.CharField("الصفة / Role", max_length=20, choices=[
        ("president", "الرئيس / Président / President"),
        ("vice_president", "نائب الرئيس وأمين المال / Vice-président et trésorier / Vice-president and treasurer"),
        ("founder", "عضو مؤسس / Membre fondateur / Founding member")])
    founder = models.BooleanField("عضو مؤسس / Founding member", default=True)
    published = models.BooleanField("ظاهر على الموقع / Visible on website", default=False)
    sort_order = models.PositiveIntegerField("الترتيب / Display order", default=0)
    panels = [FieldPanel(field) for field in ("site", "name_ar", "name_latin", "role", "founder", "published", "sort_order")]

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "عضو في الهيكلة / Leadership member"
        verbose_name_plural = "هيكلة الجمعية / Association leadership"
        constraints = [models.UniqueConstraint(fields=["site", "role"], condition=models.Q(published=True, role__in=["president", "vice_president"]), name="one_public_office_per_site")]

    def __str__(self):
        return self.name_ar + " / " + self.name_latin

    def public_values(self, language):
        labels = {
            "ar": {"president": "الرئيس", "vice_president": "نائب الرئيس وأمين المال", "founder": "عضو مؤسس"},
            "fr": {"president": "Président", "vice_president": "Vice-président et trésorier", "founder": "Membre fondateur"},
            "en": {"president": "President", "vice_president": "Vice-president and treasurer", "founder": "Founding member"},
        }
        return dict(name=self.name_ar if language == "ar" else self.name_latin,
                    role=self.role, label=labels.get(language, labels["en"])[self.role], founder=self.founder)


class MultilingualPublication(models.Model):
    site = models.OneToOneField("wagtailcore.Site", on_delete=models.PROTECT)
    version = models.CharField(max_length=40)
    digest = models.CharField(max_length=64)
    applied_at = models.DateTimeField(auto_now_add=True)
