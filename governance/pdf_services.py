"""Immutable encrypted PDF artifacts attached to existing document identities."""

import base64
import hashlib
from django.core.exceptions import ValidationError
from django.db import transaction
from . import services as s
from .models import Document, PDFArtifact
from . import pdf_design


@transaction.atomic
def artifact_for(document_id, language="ar"):
    language = language if language in pdf_design.WORDS else "ar"
    doc = Document.objects.select_for_update().get(pk=document_id)
    previous = PDFArtifact.objects.filter(document=doc, language=language).first()
    if previous:
        return previous
    body, metadata = pdf_design.render(doc, language)
    row = PDFArtifact.objects.create(
        document=doc,
        language=language,
        template_version=pdf_design.VERSION,
        payload=s.encrypt({"pdf": base64.b64encode(body).decode()}),
        sha256=hashlib.sha256(body).hexdigest(),
        metadata=metadata,
    )
    s.audit(
        None,
        "document.pdf.rendered",
        doc.serial,
        language=language,
        template=pdf_design.VERSION,
    )
    return row


def bytes_for(row):
    data = base64.b64decode(s.decrypt(row.payload)["pdf"], validate=True)
    if hashlib.sha256(data).hexdigest() != row.sha256:
        raise ValidationError("Artifact integrity failure")
    return data
