"""Private normalized portraits. Originals are discarded; issued snapshots never change."""

import base64
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from .models import Person, Portrait
from . import services as s
from .member_services import member_command

MAX_BYTES = 3 * 1024 * 1024
MAX_PIXELS = 16_000_000
CARD_KINDS = {
    "membership_card",
    "gold_card",
    "president_card",
    "vice_president_card",
    "founder_card",
    "honorary_card",
}


def owned_people(user):
    return Person.objects.filter(Q(user=user) | Q(minor=True, guardian=user))


def normalize(upload):
    """JPEG/PNG single-frame only; explicit crop preview; no facial analysis."""
    raw = upload.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValidationError("Portrait size limit exceeded")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if (
                    source.format not in {"JPEG", "PNG"}
                    or getattr(source, "n_frames", 1) != 1
                ):
                    raise ValidationError("Single JPEG or PNG required")
                w, h = source.size
                if w * h > MAX_PIXELS or min(w, h) < 300:
                    raise ValidationError("Portrait dimensions outside limits")
                source.verify()
            with Image.open(io.BytesIO(raw)) as source:
                oriented = ImageOps.exif_transpose(source)
                # Centered 4:5 crop, shown privately before administrative approval.
                w, h = oriented.size
                crop_w, crop_h = min(w, h * 4 / 5), min(h, w * 5 / 4)
                if crop_w < 300 or crop_h < 375:
                    raise ValidationError("Portrait crop too small")
                rgba = oriented.convert("RGBA")
                clean = Image.new("RGB", oriented.size, "white")
                clean.paste(rgba, mask=rgba.getchannel("A"))
                clean = ImageOps.fit(clean, (600, 750), method=Image.Resampling.LANCZOS)
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=92)
                return output.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValidationError("Invalid portrait image") from None


@member_command("portrait.upload")
def upload_portrait(*, user, person_id, image_data, consent):
    if (
        consent is not True
        or not isinstance(person_id, int)
        or isinstance(person_id, bool)
    ):
        raise ValidationError("Explicit consent and identity required")
    person = owned_people(user).select_for_update().filter(pk=person_id).first()
    if not person:
        raise PermissionDenied("Identity not owned")
    # Validate again at the service boundary; views do not determine image integrity.
    if not isinstance(image_data, str) or len(image_data) > 4 * MAX_BYTES // 3 + 4:
        raise ValidationError("Invalid portrait size")
    try:
        raw = base64.b64decode(image_data, validate=True)
    except (ValueError, TypeError):
        raise ValidationError("Invalid portrait") from None
    clean = normalize(io.BytesIO(raw))
    row = Portrait.objects.create(
        person=person,
        uploaded_by=user,
        image=s.encrypt({"jpeg": base64.b64encode(clean).decode()}),
    )
    s.audit(
        user,
        "portrait.uploaded",
        row.serial,
        person=person.pk,
        consent_version="portrait-v1",
    )
    return {"portrait": str(row.serial)}


@s.command("portrait.review")
def review_portrait(*, actor, portrait_id, decision, reason):
    from django.utils import timezone

    if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValidationError("Review reason required")
    if decision not in {"approved", "rejected"}:
        raise ValidationError("Explicit review decision required")
    row = Portrait.objects.select_for_update().get(pk=portrait_id)
    Person.objects.select_for_update().get(pk=row.person_id)
    if row.state != "pending":
        raise s.Conflict("Portrait already reviewed")
    row.state = decision
    row.reviewed_by = actor
    row.reviewed_at = timezone.now()
    row.save(update_fields=["state", "reviewed_by", "reviewed_at"])
    s.audit(actor, "portrait." + decision, row.serial, reason, person=row.person_id)
    return {"portrait": str(row.serial), "state": decision}


def snapshot_for(kind, person):
    if kind not in CARD_KINDS or person is None:
        return None
    Person.objects.select_for_update().get(pk=person.pk)
    return (
        Portrait.objects.filter(person=person, state="approved")
        .order_by("-reviewed_at", "-pk")
        .first()
    )


def portrait_bytes(row):
    return base64.b64decode(s.decrypt(row.image)["jpeg"], validate=True)
