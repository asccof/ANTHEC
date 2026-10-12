import io
from html import escape
import qrcode
import qrcode.image.svg
from django.db import transaction
from django.conf import settings
from .models import Outbox
from .services import decrypt, encrypt, public_document


def printable(doc, language="ar"):
    if doc.kind in {"professional_certificate", "accreditation_certificate"}:
        # HTML is a non-credential notice only. Certificate credentials and
        # approved artwork are delivered exclusively by the protected PDF path.
        lang = language if language in {"ar", "fr", "en"} else "ar"
        notice = {"ar": "هذه ليست شهادة صادرة أو موقعة. استعمل مسار PDF المحمي؛ التوقيع والطابع المعتمدان عند الإصدار مطلوبان.", "fr": "Ceci n’est pas un certificat émis ou signé. Utilisez le PDF protégé ; signature et cachet approuvés à l’émission sont requis.", "en": "This is not an issued or signed certificate. Use the protected PDF route; approved issuance signature and stamp are required."}[lang]
        return f'<!doctype html><html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>ANTHEC - NON-CREDENTIAL NOTICE</title><body><h1>ANTHEC</h1><p>{escape(notice)}</p></body></html>'
    data = public_document(doc)
    credentials = decrypt(doc.credentials)
    # Fragment is never sent in HTTP request URLs/referrers/access logs.
    from .institutional_labels import vocabulary, display_value

    language, labels = vocabulary(language)
    link = (
        settings.ANTHEEC_PUBLIC_ORIGIN
        + "/verify/"
        + (
            "?lang=" + language
            if doc.institutional_role_id
            or doc.membership_id
            or doc.accreditation_id
            and doc.accreditation.membership_id
            else ""
        )
        + "#"
        + credentials["token"]
    )
    qr = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage)
    output = io.BytesIO()
    qr.save(output)
    svg = output.getvalue().decode().split("?>")[-1]
    if doc.institutional_role_id:
        title = labels[doc.kind]
        direction = "rtl" if language == "ar" else "ltr"
        rows = "".join(
            f"<p>{escape(labels[k])}: {escape(display_value(labels, k, v))}</p>"
            for k, v in data.items()
        )
        return f'<!doctype html><html lang="{language}" dir="{direction}"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>{escape(title)}</title><style>body{{font-family:sans-serif;padding:30px;border:3px solid #16475b}}svg{{width:160px;height:160px}}p{{overflow-wrap:anywhere}}</style></head><body><h1>ANTHEC</h1><h2>{escape(title)}</h2>{rows}<p>{escape(labels["code"])}: {escape(credentials["code"])}</p>{svg}<p>{escape(labels["scan"])}</p><p>{escape(labels["demo"])}</p></body></html>'
    if doc.membership_id or doc.accreditation_id and doc.accreditation.membership_id:
        from .member_labels import vocabulary as member_vocabulary

        language, labels = member_vocabulary(language)
        title = labels[doc.kind]
        direction = "rtl" if language == "ar" else "ltr"
        background = "#f7e3a0" if doc.kind == "gold_card" else "#ffffff"
        rows = "".join(
            f"<p>{escape(labels[k])}: {escape(display_value(labels, k, v))}</p>"
            for k, v in data.items()
        )
        return f'<!doctype html><html lang="{language}" dir="{direction}"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>{escape(title)}</title><style>body{{font-family:sans-serif;background:{background};padding:30px}}svg{{width:160px;height:160px}}p{{overflow-wrap:anywhere}}</style></head><body><h1>ANTHEC</h1><h2>{escape(title)}</h2>{rows}<p>{escape(labels["code"])}: {escape(credentials["code"])}</p>{svg}<p>{escape(labels["scan"])}</p><p>{escape(labels["association_notice"])}</p><p>{escape(labels["demo"])}</p></body></html>'
    title = {
        "gold_card": "بطاقة عضوية ذهبية",
        "professional_certificate": "شهادة اعتماد مهني جمعوي",
        "membership_card": "بطاقة عضوية",
        "accreditation_certificate": "شهادة اعتماد",
        "invitation": "دعوة شخصية",
    }[doc.kind]
    bg = "#f7e3a0" if doc.kind == "gold_card" else "#ffffff"
    rows = "".join(f"<p>{escape(k)}: {escape(str(v))}</p>" for k, v in data.items())
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{escape(title)}</title><style>body{{font-family:sans-serif;background:{bg};padding:30px}}svg{{width:150px;height:150px}}p{{overflow-wrap:anywhere}}</style></head><body><h1>ANTHEC</h1><h2>{escape(title)}</h2>{rows}<p>رمز التحقق: {escape(credentials['code'])}</p>{svg}<p>للاطلاع على الحالة الحالية امسح QR أو أدخل المرجع ورمز التحقق.</p><p>نموذج تطوير ببيانات اصطناعية فقط. الاعتماد جمعوي وليس ترخيصًا حكوميًا.</p></body></html>"""


@transaction.atomic
def render_outbox(outbox_id):
    row = (
        Outbox.objects.select_for_update().select_related("document").get(pk=outbox_id)
    )
    if row.state in {"rendered", "retired"}:
        return row.document_id
    row.attempts += 1
    try:
        row.last_error = ""
        retry_pdf = False
        retire_pdf = False
        if row.document.rendering_state != "ready" or not row.document.rendered:
            html = printable(row.document)
            row.document.rendered = encrypt(html)
            row.document.rendering_state = "ready"
            row.document.save(update_fields=["rendered", "rendering_state"])
        from .pdf_services import artifact_for, InactiveDocument
        from .pdf_design import PendingPhoto, LayoutError
        from .certificate_assets import PendingCertificateAssets
        from .portraits import CARD_KINDS

        if row.document.kind in CARD_KINDS | {
            "professional_certificate",
            "accreditation_certificate",
        }:
            try:
                for language in ("ar", "fr", "en"):
                    artifact_for(row.document_id, language)
            except PendingPhoto:
                # HTML stays backward compatible; photo PDFs fail closed until reissue.
                row.last_error = "pending_photo"
            except PendingCertificateAssets:
                row.last_error = "pending_assets"
                retire_pdf = True  # Immutable missing snapshot cannot heal without reissuance.
            except LayoutError:
                row.last_error = "pending_layout"
            except InactiveDocument as error:
                row.last_error = "inactive_document"
                retry_pdf = error.retryable
                retire_pdf = not error.retryable
        row.state = "retired" if retire_pdf else "failed" if retry_pdf else "rendered"
        if row.last_error not in {"pending_photo", "pending_layout", "pending_assets", "inactive_document"}:
            row.last_error = ""
    except Exception:
        row.state = "failed"
        row.last_error = "render_failed"  # no sensitive exceptions logged
    row.save(update_fields=["state", "attempts", "last_error"])
    return row.document_id
