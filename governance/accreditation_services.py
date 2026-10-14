"""Private case decisions reuse the existing atomic accreditation issuance rules."""
from datetime import date
from django.core.exceptions import ValidationError
from .models import AccreditationCase, Person
from .services import command, audit, encrypt, decrypt, year_after, _issue_independent_accreditation


def validate_subject(kind, person_id, subject_name, starts_on, ends_on):
    try:
        start, end = date.fromisoformat(starts_on), date.fromisoformat(ends_on)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Valid dates required") from exc
    if kind not in {"individual", "institution", "course"} or end <= start:
        raise ValidationError("Valid kind and dates required")
    if kind != "course" and end != year_after(start):
        raise ValidationError("Annual duration required")
    if kind == "individual":
        if not person_id or subject_name.strip(): raise ValidationError("Individual subject required")
        person = Person.objects.get(pk=person_id)
        if person.verification_notice_at is None: raise ValidationError("Prior notice required")
    elif person_id or not subject_name.strip():
        raise ValidationError("Organization or course subject required")
    return start, end


def private_data(criteria, assessment, fee):
    for value in (criteria, assessment):
        if not isinstance(value, str) or len(value) > 10000:
            raise ValidationError("Bounded text required")
    # Optional internal quote only: never a public price or payment instruction.
    if fee:
        from .services import money
        amount = money(fee)
        if amount < 0: raise ValidationError("Nonnegative fee required")
        fee = str(amount)
    return {"criteria": criteria.strip(), "assessment": assessment.strip(), "fee": fee}


@command("accreditation.case.create")
def create(*, actor, kind, person_id, subject_name, starts_on, ends_on, criteria, assessment, fee, reason):
    if not reason.strip() or len(reason)>3000: raise ValidationError("Bounded reason required")
    start, end = validate_subject(kind, person_id, subject_name, starts_on, ends_on)
    payload = private_data(criteria, assessment, fee)
    payload["reason"] = reason
    row = AccreditationCase.objects.create(kind=kind, person_id=person_id,
        subject_name=subject_name.strip(), starts_on=start, ends_on=end, private_payload=encrypt(payload))
    audit(actor, "accreditation.case.created", row.pk, private_payload=row.private_payload)
    return {"case": row.pk}


@command("accreditation.case.review")
def review(*, actor, case_id, decision, criteria, assessment, fee, reason):
    row = AccreditationCase.objects.select_for_update().get(pk=case_id)
    if row.state not in {"draft", "reviewed"} or decision not in {"draft", "reviewed", "rejected"} or not reason.strip() or len(reason)>3000:
        raise ValidationError("Open case, decision and reason required")
    payload = private_data(criteria, assessment, fee)
    if decision in {"reviewed", "rejected"} and (not payload["criteria"] or not payload["assessment"]):
        raise ValidationError("Criteria and assessment required")
    payload["reason"] = reason
    row.private_payload = encrypt(payload)
    row.state = decision
    row.save(update_fields=["state", "private_payload"])
    audit(actor, "accreditation.case.reviewed", row.pk, state=decision, private_payload=row.private_payload)
    return {"case": row.pk, "state": row.state}


@command("accreditation.case.approve")
def approve(*, actor, case_id, reason):
    from .deployment import require_issuance_enabled
    require_issuance_enabled()
    if not reason.strip() or len(reason)>3000: raise ValidationError("Bounded reason required")
    row = AccreditationCase.objects.select_for_update().get(pk=case_id)
    payload = decrypt(row.private_payload)
    if row.state != "reviewed" or not payload.get("criteria") or not payload.get("assessment"):
        raise ValidationError("Completed assessment required")
    result = _issue_independent_accreditation(actor=actor, kind=row.kind, person_id=row.person_id,
        subject_name=row.subject_name, starts_on=row.starts_on.isoformat(), ends_on=row.ends_on.isoformat(), reason=f"Independent assessment case {row.pk} approved")
    row.state = "approved"
    row.accreditation_id = result["accreditation"]
    row.save(update_fields=["state", "accreditation"])
    audit(actor, "accreditation.case.approved", row.pk, accreditation=row.accreditation_id, private_payload=encrypt({"reason":reason}))
    return {"case": row.pk, **result}
