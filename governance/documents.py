import io
from html import escape
import qrcode
import qrcode.image.svg
from django.db import transaction
from django.conf import settings
from .models import Outbox
from .services import decrypt, encrypt, public_document


def printable(doc, language="ar"):
    data = public_document(doc)
    credentials = decrypt(doc.credentials)
    # Fragment is never sent in HTTP request URLs/referrers/access logs.
    from .institutional_labels import vocabulary, display_value

    language, labels = vocabulary(language)
    link = (
        settings.ANTHEEC_PUBLIC_ORIGIN
        + "/verify/"
        + ("?lang=" + language if doc.institutional_role_id else "")
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
        return f'<!doctype html><html lang="{language}" dir="{direction}"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>{escape(title)}</title><style>body{{font-family:sans-serif;padding:30px;border:3px solid #16475b}}svg{{width:160px;height:160px}}p{{overflow-wrap:anywhere}}</style></head><body><h1>ANTHEEC</h1><h2>{escape(title)}</h2>{rows}<p>{escape(labels["code"])}: {escape(credentials["code"])}</p>{svg}<p>{escape(labels["scan"])}</p><p>{escape(labels["demo"])}</p></body></html>'
    title = {
        "gold_card": "بطاقة عضوية ذهبية",
        "professional_certificate": "شهادة اعتماد مهني جمعوي",
        "membership_card": "بطاقة عضوية",
        "accreditation_certificate": "شهادة اعتماد",
        "invitation": "دعوة شخصية",
    }[doc.kind]
    bg = "#f7e3a0" if doc.kind == "gold_card" else "#ffffff"
    rows = "".join(f"<p>{escape(k)}: {escape(str(v))}</p>" for k, v in data.items())
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{escape(title)}</title><style>body{{font-family:sans-serif;background:{bg};padding:30px}}svg{{width:150px;height:150px}}p{{overflow-wrap:anywhere}}</style></head><body><h1>ANTHEEC</h1><h2>{escape(title)}</h2>{rows}<p>رمز التحقق: {escape(credentials['code'])}</p>{svg}<p>للاطلاع على الحالة الحالية امسح QR أو أدخل المرجع ورمز التحقق.</p><p>نموذج تطوير ببيانات اصطناعية فقط. الاعتماد جمعوي وليس ترخيصًا حكوميًا.</p></body></html>"""


@transaction.atomic
def render_outbox(outbox_id):
    row = (
        Outbox.objects.select_for_update().select_related("document").get(pk=outbox_id)
    )
    if row.state == "rendered":
        return row.document_id
    row.attempts += 1
    try:
        html = printable(row.document)
        row.document.rendered = encrypt(html)
        row.document.rendering_state = "ready"
        row.document.save(update_fields=["rendered", "rendering_state"])
        row.state = "rendered"
        row.last_error = ""
    except Exception:
        row.state = "failed"
        row.last_error = "render_failed"  # no sensitive exceptions logged
    row.save(update_fields=["state", "attempts", "last_error"])
    return row.document_id
