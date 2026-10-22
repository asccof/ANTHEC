"""Bounded public editorial content; never reuse private portrait/signing media."""

import base64
import io
from urllib.parse import urlsplit
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from PIL import Image, ImageOps
from .models import Activity, ActivityImage
from .services import command, audit

TEXT_FIELDS = {
    "title": 200,
    "summary": 400,
    "description": 12000,
    "programme": 6000,
    "audience": 2000,
    "speakers": 2000,
    "location": 1000,
}
CATEGORIES = ("meeting", "lecture", "workshop", "training", "conference")
FORMATS = ("online", "in_person", "hybrid")
MAX_INPUT = 3 * 1024 * 1024
MAX_IMAGES = 6


def validate_presentation(value):
    if not isinstance(value, dict) or set(value) - {
        "translations",
        "category",
        "format",
        "links",
    }:
        raise ValidationError("Invalid presentation")
    result = {
        "category": value.get("category", "meeting"),
        "format": value.get("format", "online"),
        "translations": {},
        "links": [],
    }
    if result["category"] not in CATEGORIES or result["format"] not in FORMATS:
        raise ValidationError("Invalid activity category or format")
    translations = value.get("translations", {})
    if not isinstance(translations, dict) or set(translations) - {"ar", "fr", "en"}:
        raise ValidationError("Invalid translation locale")
    for lang, content in translations.items():
        if not isinstance(content, dict) or set(content) - set(TEXT_FIELDS):
            raise ValidationError("Unknown editorial field")
        result["translations"][lang] = {}
        for field, limit in TEXT_FIELDS.items():
            text = content.get(field, "")
            if not isinstance(text, str) or len(text) > limit:
                raise ValidationError("Bounded editorial text required")
            result["translations"][lang][field] = text.strip()
    links = value.get("links", [])
    if not isinstance(links, list) or len(links) > 4:
        raise ValidationError("At most four external links")
    for link in links:
        if not isinstance(link, dict) or set(link) != {"title", "url", "kind"}:
            raise ValidationError("Invalid link")
        title, url, kind = link["title"], link["url"], link["kind"]
        if (
            not isinstance(title, str)
            or not 1 <= len(title.strip()) <= 160
            or not isinstance(url, str)
            or len(url) > 1000
            or not isinstance(kind, str)
            or kind not in {"resource", "video"}
        ):
            raise ValidationError("Invalid link fields")
        URLValidator(schemes=["https"])(url)
        parts = urlsplit(url)
        if parts.username or parts.password:
            raise ValidationError("Credentials forbidden in public links")
        result["links"].append({"title": title.strip(), "url": url, "kind": kind})
    return result


def display(row, lang):
    content = row.presentation or {}
    translations = content.get("translations", {})
    preferred = translations.get(lang, {})
    # Manual translations only; empty fields fall back to the source content.
    fallback = translations.get("ar", {})
    result = {
        key: preferred.get(key)
        or fallback.get(key)
        or next((item.get(key) for item in translations.values() if item.get(key)), "")
        for key in TEXT_FIELDS
    }
    result["title"] = preferred.get("title") or row.title
    result["category"] = content.get("category", "meeting")
    result["format"] = content.get("format", "online")
    result["links"] = content.get("links", [])
    return result


def normalize_image(raw):
    from .portraits import MAX_PIXELS
    import warnings

    if not raw or len(raw) > MAX_INPUT:
        raise ValidationError("Image limit: 3 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if (
                    source.format not in {"JPEG", "PNG"}
                    or getattr(source, "n_frames", 1) != 1
                ):
                    raise ValidationError("Single JPEG or PNG required")
                if source.width * source.height > MAX_PIXELS or min(source.size) < 120:
                    raise ValidationError("Image dimensions outside limits")
                source.verify()
            with Image.open(io.BytesIO(raw)) as source:
                swapped = source.getexif().get(274, 1) in {5, 6, 7, 8}
                source.thumbnail((1200, 1600) if swapped else (1600, 1200), Image.Resampling.LANCZOS)
                image = ImageOps.exif_transpose(source).convert("RGBA")
                clean = Image.new("RGB", image.size, "white")
                clean.paste(image, mask=image.getchannel("A"))
                output = io.BytesIO()
                clean.save(output, "JPEG", quality=85, optimize=True)
                return output.getvalue()
    except (
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValidationError("Invalid image") from None


@command("activity.publish")
def publish(*, actor, activity_id, reason):
    row = Activity.objects.select_for_update().get(pk=activity_id)
    data = validate_presentation(row.presentation)
    if not any(item.get("description") for item in data["translations"].values()):
        raise ValidationError("An activity description is required before publication")
    if not reason.strip():
        raise ValidationError("Reason required")
    row.is_published = True
    row.save(update_fields=["is_published"])
    audit(actor, "activity.published", row.pk, reason)
    return {"activity": row.pk}


@command("activity.hide")
def hide(*, actor, activity_id, reason):
    row = Activity.objects.select_for_update().get(pk=activity_id)
    if not reason.strip():
        raise ValidationError("Reason required")
    row.is_published = False
    row.save(update_fields=["is_published"])
    audit(actor, "activity.hidden", row.pk, reason)
    return {"activity": row.pk}


@command("activity.image.upload")
def upload_image(*, actor, activity_id, image_data, caption, reason):
    row = Activity.objects.select_for_update().get(pk=activity_id)
    if (
        not isinstance(image_data, str)
        or len(image_data) > 4 * MAX_INPUT // 3 + 4
        or not isinstance(caption, str)
        or len(caption) > 240
        or not reason.strip()
    ):
        raise ValidationError("Invalid image metadata")
    if row.editorial_images.filter(active=True).count() >= MAX_IMAGES:
        raise ValidationError("At most six activity images")
    try:
        raw = base64.b64decode(image_data, validate=True)
    except ValueError:
        raise ValidationError("Invalid image encoding") from None
    image = ActivityImage.objects.create(
        activity=row, jpeg=normalize_image(raw), caption=caption.strip()
    )
    audit(actor, "activity.image.uploaded", row.pk, reason, image=str(image.serial))
    return {"image": str(image.serial)}


@command("activity.image.remove")
def remove_image(*, actor, activity_id, image_serial, reason):
    row = Activity.objects.select_for_update().get(pk=activity_id)
    if not reason.strip():
        raise ValidationError("Reason required")
    image = ActivityImage.objects.select_for_update().get(
        activity=row, serial=image_serial, active=True
    )
    image.active = False
    image.save(update_fields=["active"])
    audit(actor, "activity.image.removed", row.pk, reason, image=str(image.serial))
    return {"image": str(image.serial)}
