"""Credential design proofs pending owner approval; closed assets and escaped text."""

import html
import io
import re
from pathlib import Path
from dataclasses import dataclass
from types import SimpleNamespace
from .premium_artwork import THEMES, card_background, certificate_background
import qrcode
import qrcode.image.svg
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from weasyprint import HTML
from weasyprint.urls import URLFetcher, URLFetcherResponse
from weasyprint.text.fonts import FontConfiguration
from . import services as s
from .portraits import CARD_KINDS, portrait_bytes
from . import certificate_assets as signing, certificate_content as content

ASSETS = Path(__file__).resolve().parent / "document_assets"
VERSION = "owner-review-v5.1"
CERTIFICATE_VERSION = "owner-review-v5.2-certificate-typography"
AR = "الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ"
FR = "Association Nationale de Thérapie Psychologique, Familiale et Coaching"
# Working translation submitted for owner content approval, not a registered legal name.
EN = "National Association for Psychological and Family Therapy and Coaching"
IDENTITY = {"ar": AR, "fr": FR, "en": EN}
TITLES = {
    "general": ("عضو", "Membre", "Member"),
    "affiliate": ("عضو منتسب", "Membre associé", "Associate Member"),
    "advanced": ("عضو متقدم", "Membre avancé", "Advanced Member"),
    "accredited": ("عضو معتمد", "Membre accrédité", "Accredited Member"),
    "president": ("الرئيس", "Président", "President"),
    "vice_president": ("نائب الرئيس", "Vice-président", "Vice-President"),
    "founder": ("عضو مؤسس", "Membre fondateur", "Founding Member"),
    "honorary": ("عضو شرفي", "Membre honoraire", "Honorary Member"),
    "professional_certificate": (
        "شهادة الاعتماد المهني",
        "Certificat d’accréditation professionnelle",
        "Professional Accreditation Certificate",
    ),
    "accreditation_certificate": (
        "شهادة الاعتماد",
        "Certificat d’accréditation",
        "Accreditation Certificate",
    ),
}
WORDS = {
    "ar": [
        "الصلاحية",
        "دائمة",
        "التحقق من الوثيقة",
        "مرجع الوثيقة",
        "رمز التحقق",
        "امسح QR أو أدخل المرجع ورمز التحقق.",
        "التوقيع المعتمد",
        "بداية السريان / انتهاء الصلاحية",
        "تمنح الجمعية هذه الشهادة إلى",
        "اعتماد جمعوي وفق القرار المسجل. لا يمثل ترخيصًا حكوميًا.",
    ],
    "fr": [
        "Validité",
        "Permanent",
        "Vérification du document",
        "Référence du document",
        "Code de vérification",
        "Scannez le QR ou saisissez la référence et le code.",
        "Signature autorisée",
        "Début de validité / expiration",
        "L’association décerne ce certificat à",
        "Accréditation associative selon la décision enregistrée. Ce document ne constitue pas une autorisation gouvernementale.",
    ],
    "en": [
        "Validity",
        "Permanent",
        "Credential verification",
        "Document reference",
        "Verification code",
        "Scan the QR or enter the reference and code.",
        "Authorized signature",
        "Valid from / expires",
        "The association awards this certificate to",
        "Association accreditation under the recorded decision. This document does not constitute a government licence.",
    ],
}


class PendingPhoto(ValidationError):
    pass


class LayoutError(ValidationError):
    pass


class AssetFetcher(URLFetcher):
    def __init__(self, resources):
        self.resources = resources
        self.denied = False

    def fetch(self, url, headers=None):
        if url not in self.resources:
            self.denied = True
            raise ValueError("External resource forbidden")
        body, mime = self.resources[url]
        return URLFetcherResponse(url, body=body, headers={"Content-Type": mime})


@dataclass(frozen=True)
class ParticipationProof:
    participant: str
    activity_title: str
    organizer: str
    starts_on: str
    ends_on: str
    duration: str = ""


def render_participation_proof(proof, language="ar", *, bleed=False):
    """Design proof only. No issuance record, authority, identity or verification claim."""
    if not isinstance(proof, ParticipationProof):
        raise ValidationError("Explicit participation design proof required")
    return _render(None, language, bleed=bleed, participation=proof)


def render(doc, language="ar", *, preview=False, bleed=False, proof=False):
    return _render(doc, language, preview=preview, bleed=bleed, proof=proof)


def _render(doc, language="ar", *, preview=False, bleed=False, participation=None, proof=False):
    language = language if language in WORDS else "ar"
    idx = ("ar", "fr", "en").index(language)
    rtl = language == "ar"
    words = WORDS[language]
    if participation is not None:
        doc = SimpleNamespace(kind="participation_design_proof", subject_name=participation.participant,
                              serial="NOT ISSUED", issued_at=None, portrait_id=None)
        data = {"type": "participation_design_proof", "valid_from": participation.starts_on,
                "valid_until": participation.ends_on}
        credentials = {"token": "", "code": "NOT ISSUED"}
        is_card = False
        category = "participation_design_proof"
        title = ("شهادة المشاركة", "Attestation de participation", "Certificate of Participation")[idx]
    else:
        data = s.public_document(doc)
        credentials = s.decrypt(doc.credentials)
        is_card = doc.kind in CARD_KINDS
        if not is_card and doc.kind not in {"professional_certificate", "accreditation_certificate"}:
            raise ValidationError("No approved PDF template for this document type")
        if is_card and (not doc.portrait_id or doc.portrait.state != "approved"):
            raise PendingPhoto("Approved issuance portrait missing; formal reissuance required")
        category = data["type"] if is_card else doc.kind
        if category not in TITLES:
            raise ValidationError("Unsupported approved category")
        title = TITLES[category][idx]
    certificate_assets = None
    if not is_card and participation is None:
        try:
            certificate_assets = signing.ready_assets(doc)
        except signing.PendingCertificateAssets:
            if not (proof or preview):
                raise
    official_output = bool(participation is None and not doc.is_specimen and not (preview or proof))
    signature_pending = not is_card and certificate_assets is None
    fg = THEMES[category][1] if is_card else "#173045"
    accent = THEMES[category][2] if is_card else "#216459"
    width, height = (85.6, 53.98) if is_card else (297, 210)
    pad = 3 if bleed else 0
    resources = {}

    def asset(key, body, mime):
        url = "https://document-assets.example.invalid/" + key
        resources[url] = (body, mime)
        return url

    font_css = ""
    for family, file in [
        ("IBM", "IBMPlexSansArabic-Regular"),
        ("IBMB", "IBMPlexSansArabic-SemiBold"),
        ("Naskh", "NotoNaskhArabic-Regular"),
        ("NaskhB", "NotoNaskhArabic-SemiBold"),
        ("Classic", "CormorantGaramond-Regular"),
        ("ClassicB", "CormorantGaramond-SemiBold"),
    ]:
        url = asset(
            file, (ASSETS / "fonts" / (file + ".woff2")).read_bytes(), "font/woff2"
        )
        font_css += f'@font-face{{font-family:{family};src:url("{url}")}}'
    logo = asset("logo", (ASSETS / "logo.png").read_bytes(), "image/png")
    if is_card and category == "president":
        # Preserve the owner-selected executive artwork unchanged.
        bg = asset("president", (ASSETS / "president.png").read_bytes(), "image/png")
        back_bg = bg
    else:
        bg = asset("background", card_background(category) if is_card else certificate_background(participation is not None), "image/svg+xml")
        back_bg = asset("back-background", card_background(category, back=True), "image/svg+xml") if is_card else bg
    # Issued documents retain the existing authorized origin and fragment workflow.
    link = ("ANTHEC PARTICIPATION DESIGN PROOF - NOT ISSUED" if participation else
            settings.ANTHEEC_PUBLIC_ORIGIN + "/verify/?lang=" + language + "#" + credentials["token"])
    qr = qrcode.make(
        link,
        image_factory=qrcode.image.svg.SvgPathImage,
        border=4,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    stream = io.BytesIO()
    qr.save(stream)
    qr_url = asset("qr", stream.getvalue(), "image/svg+xml")
    photo = (
        asset("portrait", portrait_bytes(doc.portrait), "image/jpeg")
        if is_card
        else None
    )
    align = "right" if rtl else "left"

    def txt(
        value,
        x,
        y,
        w,
        h,
        size=8,
        color=None,
        font="IBM",
        direction=None,
        alignment=None,
        identity=False,
    ):
        direction = direction or ("rtl" if rtl else "ltr")
        alignment = alignment or align
        return f'<div class="text {"fit" if identity else ""}" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;font-size:{size}pt;color:{color or fg};font-family:{font};direction:{direction};text-align:{alignment};unicode-bidi:plaintext">{html.escape(str(value)).replace(chr(10), "<br>")}</div>'

    def img(url, x, y, w, h, style=""):
        return f'<img src="{url}" style="position:absolute;left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;{style}">'

    def rule(x, y, w, color="#B79A58"):
        return f'<div style="position:absolute;left:{x}mm;top:{y}mm;width:{w}mm;border-top:.18mm solid {color}"></div>'

    def spec(x, y, w, color):
        if official_output:
            return ""
        label = "SPECIMEN / نموذج تجريبي" if not participation else "DESIGN PROOF / NOT ISSUED / نموذج غير صادر"
        return txt(label, x, y, w, 4, 5.2 if is_card else 7.4, color, alignment="center", direction="ltr")

    def page(content, artwork=None):
        artwork = artwork or bg
        bleed_background = img(artwork, -pad, -pad, width+2*pad, height+2*pad) if pad else ""
        return f'<section class="sheet"><div class="trim">{bleed_background}{img(artwork,0,0,width,height)}{content}</div></section>'

    validity = data["valid_from"] + " / " + (data["valid_until"] or words[1])
    if is_card:
        header = img(logo, 6.4, 4.1, 8.2, 8.2, "object-fit:contain")
        header += txt("ANTHEC", 18, 3.3, 58, 7.5, 18.5, fg, "ClassicB", direction="ltr", alignment="left")
        header += txt(IDENTITY[language], 18, 11, 60, 8.3, 6.3 if rtl else 5.9, fg,
                      "IBM", alignment="right" if rtl else "left")
        front = header + img(photo, 7, 21.7, 19.6, 24.5, "border:.22mm solid #B79A58;object-fit:contain;border-radius:.7mm")
        front += txt(title, 30.5, 21.2, 46, 6, 12.5 if rtl else 10.5, fg, "NaskhB" if rtl else "IBMB")
        front += txt(doc.subject_name, 30.5, 28.1, 46, 10.5 if category == "president" else 13.5, 15 if rtl else 11, fg,
                     "NaskhB" if rtl else "IBMB", identity=True)
        front += rule(30.5, 39.3 if category == "president" else 42.1, 46, accent)
        front += txt(words[0], 30.5, 40 if category == "president" else 43, 46, 3.1, 6.2, fg)
        if category == "president":
            # The preserved gold ribbon crosses this print zone. A small inset
            # matching the midnight field keeps dates readable without redrawing it.
            front += '<div style="position:absolute;left:30.2mm;top:43.5mm;width:47mm;height:4.2mm;background:#071521"></div>'
        front += txt(validity, 30.5, 43.8 if category == "president" else 46.1, 46, 3.8, 6.4, fg, direction="ltr")
        front += spec(13, 17.4 if category == "president" else 49.5, 59.6, fg)
        back = header + txt(words[2], 7, 19, 71, 4.6, 9.5 if rtl else 8.5, fg,
                            "NaskhB" if rtl else "IBMB")
        back += img(qr_url, 7, 24, 23, 23, "background:white")
        back += txt(words[3], 35, 24, 42, 3.4, 6.8, fg)
        back += txt(str(doc.serial)[:24]+"\n"+str(doc.serial)[24:], 35, 28, 42, 6.5, 6.4, fg,
                    direction="ltr", alignment="left")
        back += txt(words[4], 35, 35.2, 42, 3.1, 6.5, fg)
        back += txt(credentials["code"], 35, 38.5, 42, 4, 8.2, fg, "IBMB", direction="ltr", alignment="left")
        if category == "president":
            back += '<div style="position:absolute;left:34.7mm;top:42.8mm;width:43mm;height:6.9mm;background:#071521"></div>'
        back += txt(words[5], 35, 43, 42, 6.5, 6.2, fg)
        back += spec(13, 17.4 if category == "president" else 49.5, 59.6, fg)
        result = page(front) + page(back, back_bg)
    else:
        center = img(logo, 139.5, 18, 18, 18, "object-fit:contain")
        center += txt("ANTHEC", 60, 35.3, 177, 13, 28, fg, "ClassicB", direction="ltr", alignment="center")
        center += txt(IDENTITY[language], 43, 49, 211, 12, 13 if rtl else 11.5, fg,
                      "IBM", alignment="center")
        center += txt(title, 28, 62, 241, 19, 32 if rtl else 28, fg,
                      "NaskhB" if rtl else "ClassicB", alignment="center")
        wording = content.CONTENT[category][language]
        center += txt(wording[0], 37, 83, 223, 12, 14 if rtl else 12.5, "#216459", "Naskh" if rtl else "IBM", alignment="center")
        center += txt(doc.subject_name, 35, 97, 227, 19, 38 if rtl else 36, fg,
                      "NaskhB" if rtl else "ClassicB", alignment="center", identity=True)
        center += rule(99, 117, 99)
        if participation:
            center += txt(participation.activity_title, 37, 120, 223, 10, 17 if rtl else 15, fg,
                          "NaskhB" if rtl else "IBMB", alignment="center", identity=True)
            center += txt(("المنظم: ", "Organisateur : ", "Organizer: ")[idx]+participation.organizer,
                          37, 131, 223, 6, 11.5, fg, alignment="center", identity=True)
            center += txt(wording[1], 37, 138, 223, 12, 14 if rtl else 13, fg,
                          "Naskh" if rtl else "IBM", alignment="center")
            center += txt(wording[2], 37, 149, 223, 12, 12 if rtl else 11.5, fg,
                          "Naskh" if rtl else "IBM", alignment="center")
        else:
            center += txt(wording[1], 37, 120, 223, 20, 14 if rtl else 13, fg,
                          "Naskh" if rtl else "IBM", alignment="center")
            center += txt(content.scope(doc.accreditation, language), 37, 141, 223, 7, 14 if rtl else 12.5, fg,
                          "NaskhB" if rtl else "IBMB", alignment="center")
            center += txt(wording[2], 37, 149, 223, 12, 12 if rtl else 11.5, fg,
                          "Naskh" if rtl else "IBM", alignment="center")
        center += img(qr_url, 25, 169, 22, 22, "background:white")
        center += txt(words[3] if not participation else ("مرجع المشاركة: غير صادر", "Référence de participation : non émise", "Participation reference: not issued")[idx],
                      53, 166, 133, 5, 9.5, "#216459")
        center += txt(str(doc.serial), 53, 172, 133, 5, 11, fg, direction="ltr", alignment="left")
        if not participation:
            center += txt(credentials["code"], 53, 178, 48, 5, 10.5, fg, direction="ltr", alignment="left")
            issued_label = ("تاريخ الإصدار", "Date d’émission", "Issue date")[idx]
            issued_date = timezone.localdate(doc.issued_at).isoformat() if doc.issued_at else "—"
            center += txt(issued_label + " :", 106, 178, 34, 5, 9.5, "#216459")
            center += txt(issued_date, 143, 178, 43, 5, 10.5, fg, direction="ltr", alignment="left")
            center += txt(words[7], 53, 184, 133, 5, 9.5, "#216459")
            center += txt(validity, 53, 190, 133, 5, 11, fg, direction="ltr", alignment="left")
        else:
            center += txt(("تاريخ النشاط", "Dates de l’activité", "Activity dates")[idx], 53, 178, 133, 5, 9.5, "#216459")
            center += txt(validity, 53, 184, 133, 5, 11, fg, direction="ltr", alignment="left")
            if participation.duration:
                center += txt(("المدة: ", "Durée : ", "Duration: ")[idx]+participation.duration, 53, 190, 133, 5, 10.5, fg)
            center += txt(("QR تجريبي غير مفعّل", "QR de maquette non actif", "Non-operational design QR")[idx], 106, 172, 80, 5, 9.5, fg, alignment="left")
        def pending_box(x, y, w, h, label):
            return f'<div style="position:absolute;left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;border:.22mm dashed #B59A60;background:#FBF8EF"></div>' + txt(label, x+1, y+3, w-2, h-4, 8.5 if rtl else 7.8, "#75623C", "Naskh" if rtl else "IBM", alignment="center")
        if certificate_assets:
            sig, stamp = certificate_assets
            signature_url = asset("signature", signing.asset_bytes(sig), "image/png")
            stamp_url = asset("stamp", signing.asset_bytes(stamp), "image/png")
            center += img(signature_url, 195, 165, 41, 16, "object-fit:contain")
            center += img(stamp_url, 242, 163, 24, 18, "object-fit:contain")
        else:
            center += pending_box(195, 165, 41, 16, ("بانتظار التوقيع الأصلي", "Signature authentique attendue", "Awaiting authentic signature")[idx])
            center += pending_box(242, 163, 24, 18, ("بانتظار الطابع الأصلي", "Cachet authentique attendu", "Awaiting authentic stamp")[idx])
        identity = (doc.signing_snapshot if not participation else {}) or {}
        if not all(identity.get(k) for k in ("ar_name", "latin_name")):
            identity = signing.signatory_identity()
        name = identity.get("ar_name", "بانتظار هوية الموقّع المعتمدة") if rtl else identity.get("latin_name", "Awaiting approved signatory identity")
        authority_line = ("عن " + AR, "Pour l’" + FR, "For ANTHEC")[idx]
        center += txt(authority_line, 191, 181, 78, 7, 8.5 if rtl else 7.8, fg,
                      "Naskh" if rtl else "IBM", alignment="right" if rtl else "center")
        center += txt(("الرئيس", "Le Président", "President")[idx], 191, 188, 64, 4.5, 10, fg,
                      "Naskh" if rtl else "IBM", alignment="right" if rtl else "center")
        # The unsigned missing-identity notice is longer than a normal name;
        # keep it readable in the same safe slot without clipping the preview.
        name_size = (14 if rtl else 13) if identity.get("ar_name" if rtl else "latin_name") else 10.5
        center += txt(name, 191, 192.5, 64, 6, name_size, fg,
                      "NaskhB" if rtl else "ClassicB", alignment="right" if rtl else "center")
        proof_note = ("نموذج للمراجعة — غير موقّع وغير مختوم", "Maquette — non signée et non cachetée", "Review proof — unsigned and unstamped")[idx] if signature_pending else ("" if official_output else "SPECIMEN / نموذج تجريبي")
        if participation:
            proof_note += " / NOT ISSUED"
        center += txt(proof_note, 53, 161, 133, 4, 8.2, "#216459", alignment="center", direction="ltr")
        result = page(center)
    if preview:
        result = result.replace(
            "</div></section>",
            '<div style="position:absolute;left:4mm;top:4mm;color:#9A2020;font-size:7pt;font-family:IBM;background:white">PREVIEW / معاينة</div></div></section>',
        )
    css = (
        font_css
        + f"@page{{size:{width+pad*2}mm {height+pad*2}mm;margin:0;bleed:0}}*{{box-sizing:border-box}}html,body{{margin:0;padding:0}}.sheet{{position:relative;width:{width+pad*2}mm;height:{height+pad*2}mm;break-after:page;background:#FAF8F1}}.sheet:last-child{{break-after:auto}}.trim{{position:absolute;left:{pad}mm;top:{pad}mm;width:{width}mm;height:{height}mm}}.text{{position:absolute;line-height:1.15;white-space:normal;overflow-wrap:anywhere}}"
    )
    fetcher = AssetFetcher(resources)
    font_config = FontConfiguration()

    def walk(box):
        yield box
        for child in getattr(box, "children", ()):
            yield from walk(child)

    # WeasyPrint descendants() deliberately stops at absolute placeholders;
    # recurse through their children so nested fixed credential boxes are checked.
    # Bounded reflow for long holder names; never silently truncate an identity.
    for factor in (1, 0.85, 0.7, 0.6):
        # Scale every bounded identity box from its own declared size. Activity and
        # organizer fields must not inherit the much larger holder-name size.
        def fitted_size(match):
            original = float(match[2])
            size = original * factor
            if not is_card:
                # Certificates must fail layout review rather than shrinking
                # names/activities/organizers to unreadable print sizes.
                minimum = 24 if original >= 30 else 12 if original >= 15 else 10
                size = max(size, minimum)
            return match[1] + str(size) + match[3]

        adjusted = re.sub(
            r'(<div class="text fit" style="[^">]*font-size:)([0-9.]+)(pt;)',
            fitted_size,
            result,
        )
        extra = ""
        document = HTML(
            string=f'<!doctype html><html lang="{language}"><head><meta charset="utf-8"><title>ANTHEC SPECIMEN</title><style>{css}{extra}</style></head><body>{adjusted}</body></html>',
            url_fetcher=fetcher,
        ).render(font_config=font_config)
        if fetcher.denied:
            raise ValidationError("Forbidden resource requested")
        overflowing = False
        for p in document.pages:
            for box in walk(p._page_box):
                if (
                    box.element is not None
                    and ("fit" in box.element.get("class", "").split()
                         or not is_card and "text" in box.element.get("class", "").split())
                    and box.__class__.__name__ in {"AbsolutePlaceholder", "BlockBox"}
                ):
                    limit = box.position_y + box.height
                    for child in walk(box):
                        if (
                            child.__class__.__name__ == "LineBox"
                            and child.position_y + child.height > limit + 0.1
                        ):
                            if not is_card and "fit" not in box.element.get("class", "").split():
                                raise LayoutError("Certificate text needs layout review")
                            overflowing = True
        if not overflowing:
            break
    if overflowing or len(document.pages) != (2 if is_card else 1):
        raise LayoutError("Holder identity needs layout review")
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject

    reader = PdfReader(io.BytesIO(document.write_pdf(full_fonts=False)))
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
        page = writer.pages[-1]
        page.trimbox = RectangleObject(
            [
                pad * 72 / 25.4,
                pad * 72 / 25.4,
                (width + pad) * 72 / 25.4,
                (height + pad) * 72 / 25.4,
            ]
        )
        page.bleedbox = page.mediabox
    writer.add_metadata(
        {
            "/Title": "ANTHEC PARTICIPATION DESIGN PROOF - NOT ISSUED" if participation else ("ANTHEC" if official_output else "ANTHEC SPECIMEN"),
            "/Subject": "ANTHEC credential; RGB; not PDF/X" if official_output else "Synthetic non-production credential; RGB; not PDF/X",
        }
    )
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue(), {
        "width_mm": width,
        "height_mm": height,
        "bleed_mm": pad,
        "template": (VERSION if is_card else CERTIFICATE_VERSION) + ("-operational-v1" if official_output else ""),
        "language": language,
        "photo": str(doc.portrait.serial) if is_card else None,
        "font_scale": factor,
        "signing_status": "pending_authentic_assets" if signature_pending else "approved_raster_assets" if not is_card else "not_applicable",
        "signing_snapshot": (doc.signing_snapshot if not is_card and participation is None else None),
        "issued_on": timezone.localdate(doc.issued_at).isoformat() if doc.issued_at else None,
    }
