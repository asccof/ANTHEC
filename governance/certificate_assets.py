"""Primary-only protected certificate artwork; no signing recognition or issuance rules."""

import base64
import hashlib
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from . import services as s
from .models import Authority, CertificateAsset

MAX_BYTES = 3 * 1024 * 1024
CERTIFICATE_KINDS = {"professional_certificate", "accreditation_certificate"}
def signatory_identity():
    """Owner-supplied protected runtime configuration, never public person data."""
    value = getattr(settings, "ANTHEEC_CERTIFICATE_SIGNATORY", None)
    if value is None:
        return {}
    if not isinstance(value, dict) or value.get("capacity") != "president" or any(not isinstance(value.get(k), str) or not value[k].strip() or len(value[k]) > 120 for k in ("ar_name", "latin_name")):
        raise ValidationError("Approved localized signatory configuration required")
    return {k: value[k].strip() for k in ("ar_name", "latin_name", "capacity")}



class PendingCertificateAssets(ValidationError):
    pass


def normalize(upload):
    raw = upload.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValidationError("Certificate image size limit exceeded")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                w, h = source.size
                if source.format not in {"PNG", "JPEG"} or getattr(source, "n_frames", 1) != 1 or w*h > 16_000_000 or min(w, h) < 64 or max(w, h) < 300:
                    raise ValidationError("Single JPEG/PNG within image limits required")
                source.verify()
            with Image.open(io.BytesIO(raw)) as source:
                oriented = ImageOps.exif_transpose(source).convert("RGBA")
                oriented.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                clean = Image.new("RGBA", oriented.size)
                clean.paste(oriented)
                output = io.BytesIO()
                clean.save(output, "PNG")
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValidationError("Invalid certificate image") from None


@s.command("certificate.asset.upload")
def upload_asset(*, actor, kind, image_data, reason):
    if kind not in {"signature", "stamp"} or not isinstance(reason, str) or not reason.strip() or len(reason) > 1000 or not isinstance(image_data, str) or len(image_data) > 4*MAX_BYTES//3+4:
        raise ValidationError("Valid kind, reason and image required")
    try:
        clean = normalize(io.BytesIO(base64.b64decode(image_data, validate=True)))
    except (ValueError, TypeError):
        raise ValidationError("Invalid certificate image") from None
    row = CertificateAsset.objects.create(kind=kind, uploaded_by=actor, image=s.encrypt({"png": base64.b64encode(clean).decode()}), sha256=hashlib.sha256(clean).hexdigest())
    s.audit(actor, "certificate.asset.uploaded", row.serial, reason, kind=kind)
    return {"asset": str(row.serial)}


@s.command("certificate.asset.review")
def review_asset(*, actor, asset_id, decision, reason):
    if decision not in {"approved", "rejected"} or not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValidationError("Explicit approval/rejection and reason required")
    row = CertificateAsset.objects.select_for_update().get(pk=asset_id)
    if row.state != "pending":
        raise s.Conflict("Asset already reviewed")
    if decision == "approved":
        asset_bytes(row)
    old = CertificateAsset.objects.filter(kind=row.kind, state="approved").order_by("-reviewed_at", "-pk").first()
    row.state = decision
    row.reviewed_by = actor
    row.reviewed_at = timezone.now()
    row.save(update_fields=["state", "reviewed_by", "reviewed_at"])
    s.audit(actor, "certificate.asset."+decision, row.serial, reason, kind=row.kind)
    if decision == "approved" and old:
        s.audit(actor, "certificate.asset.replaced", old.serial, reason, replacement=str(row.serial), kind=row.kind)
    return {"asset": str(row.serial), "state": decision}


def snapshot_for(kind):
    if kind not in CERTIFICATE_KINDS:
        return None, None, {}
    # Same first lock as upload/review and approved issuance commands.
    Authority.objects.select_for_update().filter(pk=1).first()
    assets = [CertificateAsset.objects.filter(kind=k, state="approved").order_by("-reviewed_at", "-pk").first() for k in ("signature", "stamp")]
    signature, stamp = assets
    snapshot = {**signatory_identity(), "signature_sha256": signature.sha256 if signature else None, "stamp_sha256": stamp.sha256 if stamp else None}
    return signature, stamp, snapshot


def asset_bytes(row):
    data = base64.b64decode(s.decrypt(row.image)["png"], validate=True)
    if hashlib.sha256(data).hexdigest() != row.sha256:
        raise ValidationError("Certificate asset integrity failure")
    return data


def ready_assets(doc):
    snapshot = doc.signing_snapshot or {}
    if snapshot.get("capacity") != "president" or not all(isinstance(snapshot.get(k), str) and snapshot[k].strip() for k in ("ar_name", "latin_name")):
        raise PendingCertificateAssets("Approved issuance signatory identity missing; formal reissuance required")
    rows = (doc.signature_asset, doc.stamp_asset)
    if not all(rows):
        raise PendingCertificateAssets("Authentic approved issuance signature/stamp missing; formal reissuance required")
    for row, kind in zip(rows, ("signature", "stamp")):
        if row.state != "approved" or row.kind != kind or snapshot.get(kind+"_sha256") != row.sha256:
            raise ValidationError("Approved immutable signing snapshot required")
        asset_bytes(row)
    return rows
