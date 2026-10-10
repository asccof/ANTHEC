"""Immutable encrypted PDF artifacts attached to existing document identities."""

import base64
import hashlib
from django.core.exceptions import ValidationError
from django.db import transaction
from . import services as s
from .models import Document, PDFArtifact, Membership, Accreditation, InstitutionalRole
from . import pdf_design


class InactiveDocument(ValidationError):
    def __init__(self, status, *, retryable=False):
        self.status = status
        self.retryable = retryable
        super().__init__("Document lifecycle does not permit PDF generation")


def retryable_inactive(doc):
    """Queue classification from the existing lifecycle, not a new state decision."""
    if doc.void or doc.registration_id:
        return False
    origin = (doc.institutional_role if doc.institutional_role_id else
              doc.membership if doc.membership_id else doc.accreditation)
    if origin.ends_on and s.today() >= origin.ends_on:
        return False
    if doc.institutional_role_id and (
        origin.state == "terminated" or
        origin.role != "founder" and origin.state == "cancelled"
    ):
        return False
    if doc.accreditation_id and origin.membership_id:
        term = origin.membership
        if term.ends_on and s.today() >= term.ends_on:
            return False
    return True


def locked_document(document_id):
    """Call inside an atomic boundary; retain locks through generation/delivery."""
    doc = Document.objects.select_for_update().get(pk=document_id)
    # Lock the records changed by the existing lifecycle commands too. Linked
    # membership precedes accreditation, matching membership-state propagation.
    if doc.institutional_role_id:
        doc.institutional_role = InstitutionalRole.objects.select_for_update().get(
            pk=doc.institutional_role_id
        )
    elif doc.membership_id:
        doc.membership = Membership.objects.select_for_update().get(pk=doc.membership_id)
    elif doc.accreditation_id:
        membership_id = Accreditation.objects.values_list("membership_id", flat=True).get(
            pk=doc.accreditation_id
        )
        membership = (
            Membership.objects.select_for_update().get(pk=membership_id)
            if membership_id else None
        )
        doc.accreditation = Accreditation.objects.select_for_update().get(
            pk=doc.accreditation_id
        )
        if membership:
            doc.accreditation.membership = membership
    return doc


@transaction.atomic
def artifact_for(document_id, language="ar"):
    language = language if language in pdf_design.WORDS else "ar"
    doc = locked_document(document_id)
    status = s.document_status(doc)
    if status in {"cancelled", "suspended", "expired"}:
        raise InactiveDocument(status, retryable=retryable_inactive(doc))
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
