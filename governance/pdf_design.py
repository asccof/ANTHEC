"""Owner-approved v4 layout. Fixed assets and escaped text; no external fetches."""

import html
import io
from pathlib import Path
import qrcode
import qrcode.image.svg
from django.core.exceptions import ValidationError
from django.conf import settings
from weasyprint import HTML
from weasyprint.urls import URLFetcher, URLFetcherResponse
from weasyprint.text.fonts import FontConfiguration
from . import services as s
from .portraits import CARD_KINDS, portrait_bytes

ASSETS = Path(__file__).resolve().parent / "document_assets"
VERSION = "approved-v4.1"
AR = "الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ"
FR = "Association Nationale de Thérapie Psychologique, Familiale et Coaching"
TITLES = {
    "general": ("عضو عام", "Membre général", "General Member"),
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
        "الإصدار / انتهاء الصلاحية",
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
        "Émission / expiration",
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
        "Issued / expires",
        "The association awards this certificate to",
        "Association accreditation under the recorded decision. This document does not constitute a government licence.",
    ],
}
PALETTES = {
    "general": ("#FCFCF8", "#122E3B", "#237C9D"),
    "affiliate": ("#071E2B", "#FFFFFF", "#55CFCC"),
    "advanced": ("#09263F", "#FFFFFF", "#D3DAE0"),
    "vice_president": ("#071E2B", "#FFFFFF", "#DFD4B6"),
    "founder": ("#104B3E", "#FFFFFF", "#E9D4A6"),
    "honorary": ("#FAF7EC", "#122E3B", "#9A7837"),
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


def generic_background(category):
    bg, fg, gold = PALETTES[category]
    curves = "".join(
        f'<path d="M-20 {i*7} Q430 {i*7-140} 900 {i*7+70}"/>' for i in range(40)
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 856 540"><rect width="856" height="540" fill="{bg}"/><g fill="none" stroke="{gold}" stroke-width=".6" opacity=".18">{curves}</g><path d="M-40 200 Q150 500 920 430 L920 466 Q80 610 -40 270Z" fill="{gold}" opacity=".85"/><rect x="14" y="14" width="828" height="512" rx="24" fill="none" stroke="{gold}" stroke-width="3"/><rect x="21" y="21" width="814" height="498" rx="21" fill="none" stroke="{gold}" stroke-width=".8"/></svg>'.encode()


def render(doc, language="ar", *, preview=False, bleed=False):
    language = language if language in WORDS else "ar"
    idx = ("ar", "fr", "en").index(language)
    rtl = language == "ar"
    words = WORDS[language]
    data = s.public_document(doc)
    credentials = s.decrypt(doc.credentials)
    is_card = doc.kind in CARD_KINDS
    if not is_card and doc.kind not in {
        "professional_certificate",
        "accreditation_certificate",
    }:
        raise ValidationError("No approved PDF template for this document type")
    if is_card and (not doc.portrait_id or doc.portrait.state != "approved"):
        raise PendingPhoto(
            "Approved issuance portrait missing; formal reissuance required"
        )
    category = data["type"] if is_card else doc.kind
    if category not in TITLES:
        raise ValidationError("Unsupported approved category")
    title = TITLES[category][idx]
    dark = is_card and category not in {"general", "accredited", "honorary"}
    fg = "#FFFFFF" if dark else "#122E3B"
    accent = "#EADBB9" if dark else "#216459"
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
    if not is_card:
        bg = asset(
            "certificate", (ASSETS / "certificate.svg").read_bytes(), "image/svg+xml"
        )
    elif category == "accredited":
        bg = asset("gold", (ASSETS / "gold.png").read_bytes(), "image/png")
    elif category == "president":
        bg = asset("president", (ASSETS / "president.png").read_bytes(), "image/png")
    else:
        bg = asset("background", generic_background(category), "image/svg+xml")
    link = (
        settings.ANTHEEC_PUBLIC_ORIGIN
        + "/verify/?lang="
        + language
        + "#"
        + credentials["token"]
    )
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

    def spec(x, y, w, color):
        return txt(
            "SPECIMEN / نموذج تجريبي",
            x,
            y,
            w,
            6,
            5.8 if is_card else 8,
            color,
            alignment="center",
        )

    def page(content):
        return f'<section class="sheet"><div class="trim">{img(bg,-pad,-pad,width+2*pad,height+2*pad)}{content}</div></section>'

    validity = data["valid_from"] + " / " + (data["valid_until"] or words[1])
    if is_card:
        header = img(logo, 5.5, 4.3, 8.5, 8.5) + txt(
            "ANTHEC",
            18,
            3.4,
            57,
            8,
            19,
            "#EADBB9" if dark else fg,
            "ClassicB",
            direction="ltr",
            alignment="left",
        )
        front = header + txt(
            AR, 18, 11.3, 60, 6, 6.8, fg, direction="rtl", alignment="right"
        )
        front += img(
            photo, 7, 21, 18.4, 23, "border:.2mm solid #AC8B4C;object-fit:contain"
        )
        front += txt(
            title,
            30,
            21,
            46.5,
            6.6,
            13 if rtl else 11,
            accent,
            "NaskhB" if rtl else "IBMB",
        )
        front += txt(
            doc.subject_name,
            30,
            28.7,
            46.5,
            10.5,
            15 if rtl else 10.6,
            fg,
            "NaskhB" if rtl else "IBMB",
            identity=True,
        )
        front += txt(
            str(doc.serial),
            30,
            17.4,
            46.5,
            3.2,
            5.8,
            fg,
            direction="ltr",
            alignment="left",
        )
        front += txt(words[0], 30, 40, 46.5, 3.5, 6.5, accent)
        front += f'<div style="position:absolute;left:29.7mm;top:43.5mm;width:47mm;height:4.2mm;background:{"#071E2B" if dark else "transparent"}"></div>'
        front += txt(validity, 30, 43.8, 46.5, 4, 6.7, fg, direction="ltr")
        front += (
            '<div style="position:absolute;left:7mm;top:44.7mm;width:22mm;height:6.3mm;background:#FAF8F1"></div>'
            + spec(7, 45, 22, "#122E3B")
        )
        back = header + txt(
            words[2], 18, 11, 60, 5.5, 9, fg, "NaskhB" if rtl else "IBM"
        )
        back += (
            '<div style="position:absolute;left:7mm;top:18mm;width:23mm;height:23mm;background:white"></div>'
            + img(qr_url, 7, 18, 23, 23)
        )
        back += txt(words[3], 34, 18, 43, 4, 7.2, accent) + txt(
            str(doc.serial)[:24] + "\n" + str(doc.serial)[24:],
            34,
            22,
            43,
            7,
            6.8,
            fg,
            direction="ltr",
        )
        back += txt(words[4], 34, 29.5, 43, 4, 7.2, accent) + txt(
            credentials["code"], 34, 34, 43, 4.5, 9.4, fg, "IBMB", direction="ltr"
        )
        back += (
            '<div style="position:absolute;left:6.5mm;top:41.2mm;width:24mm;height:6.2mm;background:'
            + ("#071E2B" if dark else "#FAF8F1")
            + '"></div>'
            + spec(6.5, 41.3, 24, accent)
        )
        back += txt(words[5], 33, 40.5, 44, 9, 6.6, fg)
        result = page(front) + page(back)
    else:
        center = img(logo, 133, 20, 19, 19) + txt(
            "ANTHEC",
            65,
            39,
            167,
            15,
            32,
            "#122E3B",
            "ClassicB",
            direction="ltr",
            alignment="center",
        )
        center += txt(
            FR if language == "fr" else AR,
            43,
            53.5,
            211,
            10,
            10.8 if language == "fr" else 14,
            "#122E3B",
            direction="ltr" if language == "fr" else "rtl",
            alignment="center",
        )
        center += txt(
            title,
            38,
            70,
            221,
            18,
            31 if rtl else 24,
            "#122E3B",
            "NaskhB" if rtl else "ClassicB",
            alignment="center",
        )
        center += txt(
            words[8],
            40,
            91,
            217,
            9,
            12,
            "#216459",
            "Naskh" if rtl else "IBM",
            alignment="center",
        )
        center += txt(
            doc.subject_name,
            42,
            103,
            213,
            21,
            32 if rtl else 28,
            "#122E3B",
            "NaskhB" if rtl else "ClassicB",
            alignment="center",
            identity=True,
        )
        center += '<div style="position:absolute;left:94mm;top:130mm;width:109mm;border-top:.2mm solid #AC8B4C"></div>'
        center += txt(
            words[9],
            43,
            135,
            211,
            15,
            11.5,
            "#122E3B",
            "Naskh" if rtl else "IBM",
            alignment="center",
        )
        center += (
            '<div style="position:absolute;left:30mm;top:160mm;width:24mm;height:24mm;background:white"></div>'
            + img(qr_url, 30, 160, 24, 24)
        )
        center += txt(words[3], 63, 158, 119, 4.5, 7.5, "#216459") + txt(
            str(doc.serial), 63, 164, 119, 5, 8.2, "#122E3B", direction="ltr"
        )
        center += txt(
            credentials["code"], 63, 170, 119, 5, 8.5, "#122E3B", direction="ltr"
        )
        center += txt(words[7], 63, 177, 119, 4.5, 7.5, "#216459") + txt(
            validity, 63, 183, 119, 5, 8.5, "#122E3B", direction="ltr"
        )
        center += (
            '<div style="position:absolute;left:207mm;top:169mm;width:56mm;border-top:.2mm solid #AC8B4C"></div>'
            + txt(
                words[6],
                206,
                173,
                58,
                8,
                10,
                "#122E3B",
                "Naskh" if rtl else "IBM",
                alignment="center",
            )
        )
        center += spec(205, 22, 58, "#216459")
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
        adjusted = (
            result
            if factor == 1
            else result.replace(
                'class="text fit"', f'class="text fit" data-fit="{factor}"'
            )
        )
        extra = (
            ""
            if factor == 1
            else f".fit{{font-size:{(15 if rtl else 10.6)*factor if is_card else (32 if rtl else 28)*factor}pt!important}}"
        )
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
                    and "fit" in box.element.get("class", "").split()
                    and box.__class__.__name__ in {"AbsolutePlaceholder", "BlockBox"}
                ):
                    limit = box.position_y + box.height
                    for child in walk(box):
                        if (
                            child.__class__.__name__ == "LineBox"
                            and child.position_y + child.height > limit + 0.1
                        ):
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
            "/Title": "ANTHEC SPECIMEN",
            "/Subject": "Synthetic non-production credential; RGB; not PDF/X",
        }
    )
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue(), {
        "width_mm": width,
        "height_mm": height,
        "bleed_mm": pad,
        "template": VERSION,
        "language": language,
        "photo": str(doc.portrait.serial) if is_card else None,
        "font_scale": factor,
    }
