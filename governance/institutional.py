"""Phase 1 institutional decisions reuse the authorized transactional boundary."""

from datetime import date
from django.core.exceptions import ValidationError
from .models import InstitutionalRole, Person
from .services import command, issue, audit, Conflict

ROLES = {"president", "vice_president", "founder", "honorary"}
PERMANENT_ROLES = {"founder", "honorary"}


@command("institutional.grant")
def grant(
    *,
    actor,
    person_id,
    role,
    starts_on,
    ends_on,
    legal_reference,
    reason,
    replaces_role_id=None
):
    if (
        role not in ROLES
        or not isinstance(legal_reference, str)
        or not legal_reference.strip()
        or len(legal_reference) > 120
        or not reason.strip()
    ):
        raise ValidationError("Recorded role, decision reference and reason required")
    person = Person.objects.select_for_update().get(pk=person_id)
    if person.verification_notice_at is None:
        raise ValidationError("Prior verification notice required")
    try:
        start = date.fromisoformat(starts_on)
        end = date.fromisoformat(ends_on) if ends_on else None
    except (TypeError, ValueError):
        raise ValidationError("Explicit legal dates required")
    if role in PERMANENT_ROLES:
        if end or replaces_role_id:
            raise ValidationError(
                "This designation is permanent; replace its document instead"
            )
        if InstitutionalRole.objects.filter(person=person, role=role).exists():
            raise Conflict("Permanent designation already recorded")
    elif end is None or end <= start:
        raise ValidationError("Explicit recorded legal office end required")
    previous = None
    if replaces_role_id:
        previous = InstitutionalRole.objects.select_for_update().get(
            pk=replaces_role_id
        )
        if (
            previous.role != role
            or previous.state not in {"active", "suspended"}
            or InstitutionalRole.objects.filter(replaces=previous).exists()
        ):
            raise Conflict("Replace a matching, unreplaced office record")
    # Only duplicate/overlapping grants to the same person+role are constrained.
    # Global office headcounts are not invented by this implementation.
    if role not in PERMANENT_ROLES:
        overlaps = InstitutionalRole.objects.filter(
            person=person,
            role=role,
            state__in=["active", "suspended"],
            starts_on__lt=end,
            ends_on__gt=start,
        )
        if previous:
            overlaps = overlaps.exclude(pk=previous.pk)
        if overlaps.exists():
            raise Conflict("Overlapping office eligibility")
    row = InstitutionalRole.objects.create(
        person=person,
        role=role,
        starts_on=start,
        ends_on=end,
        legal_reference=legal_reference.strip(),
        replaces=previous,
    )
    doc = issue(role + "_card", institutional_role=row)
    if previous:
        previous.state = "terminated"
        previous.save(update_fields=["state"])
        audit(
            actor, "institutional.terminated", previous.pk, reason, replacement=row.pk
        )
    audit(
        actor,
        "institutional.granted",
        row.pk,
        reason,
        role=role,
        starts_on=str(start),
        ends_on=str(end) if end else None,
        policy="owner-phase1-2026-10-10",
    )
    return {"institutional_role": row.pk, "document": doc.pk}


@command("institutional.state")
def change_state(*, actor, role_id, state, reason):
    row = InstitutionalRole.objects.select_for_update().get(pk=role_id)
    if (
        state not in {"active", "suspended", "cancelled", "terminated"}
        or not reason.strip()
    ):
        raise ValidationError("Documented state decision required")
    if state == "terminated" and row.role in PERMANENT_ROLES:
        raise ValidationError("Permanent designation has no office term")
    if row.state == "terminated" or (
        row.role not in PERMANENT_ROLES and row.state == "cancelled" and state != "terminated"
    ):
        raise Conflict("New recorded office appointment required")
    # A renewed/reactivated period must not coexist with an overlapping office grant.
    if state == "active" and row.role not in PERMANENT_ROLES:
        if (
            InstitutionalRole.objects.filter(
                person=row.person,
                role=row.role,
                state__in=["active", "suspended"],
                starts_on__lt=row.ends_on,
                ends_on__gt=row.starts_on,
            )
            .exclude(pk=row.pk)
            .exists()
        ):
            raise Conflict("Overlapping office eligibility")
    row.state = state
    row.save(update_fields=["state"])
    audit(actor, "institutional." + state, row.pk, reason)
    return {"institutional_role": row.pk, "state": state}
