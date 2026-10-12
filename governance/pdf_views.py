from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import Document, PDFArtifact
from . import portraits, services as s, pdf_services, pdf_design
from .member_labels import vocabulary


def document_person(doc):
    return (
        doc.institutional_role.person
        if doc.institutional_role_id
        else (
            doc.membership.application.person
            if doc.membership_id
            else (
                doc.accreditation.person
                if doc.accreditation_id
                else doc.registration.person
            )
        )
    )


def permitted(request, doc):
    person = document_person(doc)
    own = person and portraits.owned_people(request.user).filter(pk=person.pk).exists()
    if own:
        return "owned"
    try:
        with transaction.atomic():
            s.authorize(request)
    except (PermissionDenied, ObjectDoesNotExist):
        return False
    return "administrative"


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["GET"])
@transaction.atomic
def download(request, document_id, preview=False):
    doc = get_object_or_404(Document, pk=document_id)
    access = permitted(request, doc)
    if not access:
        return HttpResponse(status=404)
    # Administrative authority is acquired before Document, matching command
    # lock order. Keep document/origin locks through audit and response creation.
    doc = pdf_services.locked_document(document_id)
    if access == "owned" and not portraits.owned_people(request.user).filter(
        pk=document_person(doc).pk
    ).exists():
        return HttpResponse(status=404)
    lang, _ = vocabulary(request.GET.get("lang", "ar"))
    status = s.document_status(doc)
    if status in {"cancelled", "suspended", "expired"}:
        return HttpResponse(
            {
                "ar": "الوثيقة غير سارية. راجع سجل الحالة.",
                "fr": "Document non valide. Consultez son historique.",
                "en": "Document is not valid. Consult its status history.",
            }[lang],
            status=410,
        )
    try:
        if preview:
            body, _ = pdf_design.render(doc, lang, preview=True)
        else:
            artifact = PDFArtifact.objects.filter(document=doc, language=lang).first()
            if artifact is None:
                if doc.kind in portraits.CARD_KINDS and not doc.portrait_id:
                    raise pdf_design.PendingPhoto("Issuance portrait missing")
                return HttpResponse(
                    {
                        "ar": "PDF ينتظر التوليد المحمي.",
                        "fr": "PDF en attente de génération autorisée.",
                        "en": "PDF awaits protected generation.",
                    }[lang],
                    status=409,
                )
            body = pdf_services.bytes_for(artifact)
    except pdf_design.PendingPhoto:
        return HttpResponse(
            {
                "ar": "بانتظار الصورة المقبولة عند الإصدار. يلزم إعادة إصدار رسمية للوثيقة الحالية.",
                "fr": "Portrait approuvé manquant à l’émission. Réémission formelle requise.",
                "en": "Approved portrait missing at issuance. Formal reissuance required.",
            }[lang],
            status=409,
        )
    except pdf_design.LayoutError:
        return HttpResponse(
            {
                "ar": "الاسم يحتاج مراجعة التكوين قبل إخراج الوثيقة.",
                "fr": "Le nom nécessite une révision de mise en page.",
                "en": "Holder name requires layout review.",
            }[lang],
            status=409,
        )
    except ValidationError:
        return HttpResponse(status=409)
    # Recheck time-based expiry too after rendering, while lifecycle locks remain.
    status = s.document_status(doc)
    if status in {"cancelled", "suspended", "expired"}:
        return HttpResponse(status=410)
    s.audit(
        request.user,
        "document.pdf.previewed" if preview else "document.pdf.downloaded",
        doc.serial,
        language=lang,
        status=status,
    )
    response = HttpResponse(body, content_type="application/pdf")
    response["Content-Disposition"] = (
        "inline" if preview else "attachment"
    ) + f'; filename="ANTHEC-{doc.serial}-{lang}.pdf"'
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Document-Status"] = status
    return response


@never_cache
@login_required(login_url="/members/login/")
@require_http_methods(["POST"])
@transaction.atomic
def prepare(request, document_id):
    from django.shortcuts import redirect
    from django.urls import reverse

    doc = get_object_or_404(Document, pk=document_id)
    if not permitted(request, doc):
        return HttpResponse(status=404)
    language, _ = vocabulary(request.GET.get("lang", "ar"))
    try:
        pdf_services.artifact_for(doc.pk, language)
    except pdf_services.InactiveDocument:
        return HttpResponse(status=410)
    except (ValidationError, ObjectDoesNotExist):
        # Reuse localized pending-photo/layout feedback without creating an artifact.
        return HttpResponse(
            {
                "ar": "تعذر التوليد؛ راجع صورة الإصدار والتكوين والتوقيع والطابع المعتمدين. يلزم إعادة إصدار عند غياب لقطة الإصدار.",
                "fr": "Génération impossible : vérifiez le portrait, la mise en page, la signature et le cachet approuvés à l’émission. Réémission requise si un instantané manque.",
                "en": "Generation unavailable. Check approved issuance portrait, layout, signature and stamp; formal reissuance is required when an issuance snapshot is missing.",
            }[language],
            status=409,
        )
    s.audit(request.user, "document.pdf.prepared", doc.serial, language=language)
    return redirect(reverse("document_pdf", args=[doc.pk]) + "?lang=" + language)
