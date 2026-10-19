"""Administrative activity configuration; admission/attendance keep existing commands."""

from datetime import date
from django.core.exceptions import ValidationError
from .models import Activity, Registration
from .services import command, audit


def validated(
    title,
    starts_on,
    ends_on,
    capacity,
    allows_minors,
    consent_version,
    consent_text,
    reason,
    presentation=None,
):
    for value, limit in (
        (title, 200),
        (consent_version, 60),
        (consent_text, 10000),
        (reason, 3000),
    ):
        if not isinstance(value, str) or len(value) > limit:
            raise ValidationError("Bounded text required")
    if not title.strip() or not reason.strip():
        raise ValidationError("Title and reason required")
    try:
        start, end = date.fromisoformat(starts_on), date.fromisoformat(ends_on)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Valid dates required") from exc
    if (
        end < start
        or not isinstance(capacity, int)
        or isinstance(capacity, bool)
        or not 1 <= capacity <= 100000
        or not isinstance(allows_minors, bool)
    ):
        raise ValidationError("Valid dates, capacity and minor eligibility required")
    if allows_minors and (not consent_text.strip() or not consent_version.strip()):
        raise ValidationError("Explicit versioned guardian consent required")
    return dict(
        title=title.strip(),
        starts_on=start,
        ends_on=end,
        capacity=capacity,
        allows_minors=allows_minors,
        consent_version=consent_version.strip(),
        consent_text=consent_text.strip(),
    )


@command("activity.create")
def create(*, actor, **payload):
    data = validated(**payload)
    if payload.get("presentation") is not None:
        from .activity_editorial import validate_presentation

        data["presentation"] = validate_presentation(payload["presentation"])
    row = Activity.objects.create(**data)
    audit(actor, "activity.created", row.pk, payload["reason"])
    return {"activity": row.pk}


@command("activity.update")
def update(*, actor, activity_id, **payload):
    data = validated(**payload)
    row = Activity.objects.select_for_update().get(pk=activity_id)
    if payload.get("presentation") is not None:
        from .activity_editorial import validate_presentation

        data["presentation"] = validate_presentation(payload["presentation"])
    if Registration.objects.filter(activity=row).exists():
        for field in (
            "starts_on",
            "ends_on",
            "allows_minors",
            "consent_version",
            "consent_text",
        ):
            if getattr(row, field) != data[field]:
                raise ValidationError(
                    "Existing participant conditions are immutable; create a separate activity"
                )
    if (
        Registration.objects.filter(activity=row, state="confirmed").count()
        > data["capacity"]
    ):
        raise ValidationError("Capacity below confirmed participants")
    for name, value in data.items():
        setattr(row, name, value)
    row.save()
    audit(actor, "activity.updated", row.pk, payload["reason"], capacity=row.capacity)
    return {"activity": row.pk}
