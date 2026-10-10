"""Approved POL-01..08 command boundary. No ordinary domain CRUD is exposed."""

import base64
import hashlib
import json
import secrets
from datetime import date
from decimal import Decimal
from functools import wraps
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from cryptography.fernet import Fernet
from .models import (
    Authority,
    Delegation,
    Audit,
    Command,
    Price,
    Application,
    Payment,
    Exemption,
    Membership,
    Accreditation,
    Document,
    Outbox,
    Refund,
    Registration,
    Attendance,
    Person,
    Activity,
)

TIERS = {
    "general": 100,
    "affiliate": 500,
    "advanced": 1500,
    "accredited": 3000,
    "founder": 0,
    "honorary": 0,
}
POLICY_VERSION = "owner-2026-10-10-v1"


class Conflict(ValidationError):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def money(value):
    try:
        amount = Decimal(str(value))
        if (
            not amount.is_finite()
            or amount.as_tuple().exponent < -2
            or abs(amount) >= Decimal("100000000")
        ):
            raise ValueError()
        return amount
    except Exception as exc:
        raise ValidationError("Invalid monetary amount") from exc


def cipher():
    key = settings.ANTHEEC_DATA_KEY
    if not key:
        raise ValidationError("ANTHEEC_DATA_KEY is required for document credentials.")
    return Fernet(key.encode())


def encrypt(value):
    return cipher().encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()


def decrypt(value):
    return json.loads(cipher().decrypt(value.encode()))


def today():
    return timezone.localdate()


def year_after(day):
    # Engineering rule authorized by POL-02: exclusive end; Feb 29 -> Feb 28.
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)


def audit(user, action, subject, reason="", **details):
    return Audit.objects.create(
        actor=user, action=action, subject=str(subject), reason=reason, details=details
    )


def authorize(request, primary_only=False, recent=True):
    authority = Authority.objects.select_for_update().get(pk=1)
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")
    user.refresh_from_db()
    if not user.is_active or not user.is_verified():
        raise PermissionDenied("Administrative MFA required")
    if authority.primary_id == user.pk:
        epoch = 0
    else:
        if primary_only:
            raise PermissionDenied("Primary director only")
        delegation = (
            Delegation.objects.select_for_update()
            .filter(user=user, active=True)
            .first()
        )
        if not delegation:
            raise PermissionDenied("No active delegation")
        epoch = delegation.epoch
    if request.session.get("authority_epoch") != epoch:
        raise PermissionDenied("Administrative session revoked")
    verified_at = request.session.get("reauth_at", 0)
    if recent and not 0 <= timezone.now().timestamp() - verified_at <= 300:
        raise PermissionDenied("Recent password and second factor required")
    return user


def command(action, primary_only=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *, key, **payload):
            if not key or len(key) > 120:
                raise ValidationError("Invalid command key")
            with transaction.atomic():
                actor = authorize(request, primary_only=primary_only)
                hashed = digest(json.dumps(payload, sort_keys=True, default=str))
                previous = Command.objects.filter(
                    actor=actor, action=action, key=key
                ).first()
                if previous:
                    if previous.digest != hashed:
                        raise Conflict("Key reused with different input")
                    return previous.result
                result = fn(actor=actor, **payload)
                Command.objects.create(
                    actor=actor, action=action, key=key, digest=hashed, result=result
                )
                return result

        return wrapper

    return decorator


@command("delegate", primary_only=True)
def delegate(*, actor, user_id, active, reason):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission, Group

    authority = Authority.objects.get(pk=1)
    if (
        not isinstance(active, bool)
        or user_id == authority.primary_id
        or not reason.strip()
    ):
        raise ValidationError("Primary director cannot be changed; reason required")
    target = get_user_model().objects.select_for_update().get(pk=user_id)
    if target.is_superuser:
        raise ValidationError("Delegates cannot be Django superusers")
    row, _ = Delegation.objects.get_or_create(user=target)
    row.active = bool(active)
    row.epoch += 1
    row.save()
    # Business operations are authorized by delegation, not Django superuser.
    group, _ = Group.objects.get_or_create(name="ANTHEEC operational directors")
    if active:
        permissions = Permission.objects.filter(
            content_type__app_label__in=["wagtailadmin", "wagtailimages", "wagtaildocs"]
        )
        group.permissions.set(permissions)
        from wagtail.models import GroupPagePermission, Page

        for name in [
            "add_page",
            "change_page",
            "publish_page",
            "lock_page",
            "unlock_page",
        ]:
            permission = Permission.objects.filter(
                content_type__app_label="wagtailcore", codename=name
            ).first()
            if permission:
                GroupPagePermission.objects.get_or_create(
                    group=group, page=Page.get_first_root_node(), permission=permission
                )
        target.groups.add(group)
    else:
        target.groups.remove(group)
    audit(
        actor,
        "delegation.changed",
        row.pk,
        reason,
        active=bool(active),
        epoch=row.epoch,
    )
    return {"delegation": row.pk, "active": row.active}


@command("price.change")
def change_price(*, actor, tier, amount, starts_at):
    from django.utils.dateparse import parse_datetime

    moment = parse_datetime(starts_at)
    if moment is None or timezone.is_naive(moment):
        raise ValidationError("Timezone-aware price start required")
    amount = money(amount)
    if (
        tier not in TIERS
        or tier in {"founder", "honorary"}
        or amount < 0
        or moment < timezone.now()
    ):
        raise ValidationError("Invalid prospective price")
    price = Price.objects.create(
        tier=tier, amount=amount, starts_at=moment, created_by=actor
    )
    audit(
        actor,
        "price.changed",
        price.pk,
        tier=tier,
        amount=str(amount),
        starts_at=starts_at,
    )
    return {"price": price.pk}


def create_application(person, tier, previous=None):
    if tier not in TIERS or person.verification_notice_at is None:
        raise ValidationError(
            "Valid tier and verification notice acknowledgment required"
        )
    if previous and (
        previous.application.person_id != person.pk or previous.application.tier != tier
    ):
        raise ValidationError("Renewal must match the existing person and tier")
    day = today()
    price = (
        Price.objects.filter(tier=tier, starts_at__lte=timezone.now())
        .order_by("-starts_at", "-pk")
        .first()
    )
    if tier not in {"founder", "honorary"} and price is None:
        raise ValidationError("Seed approved prices before fixing a quote")
    return Application.objects.create(
        person=person,
        tier=tier,
        previous=previous,
        quoted_on=day,
        price=price,
        quote=price.amount if price else 0,
    )


@command("payment.verify")
def verify_payment(*, actor, application_id, amount, method, proof_reference):
    app = Application.objects.select_for_update().get(pk=application_id)
    amount = money(amount)
    if (
        method not in {"cash", "transfer"}
        or amount <= 0
        or not proof_reference.strip()
        or app.state != "submitted"
    ):
        raise ValidationError("Invalid payment verification")
    row = Payment.objects.create(
        application=app,
        amount=amount,
        method=method,
        proof_reference=proof_reference,
        verified_by=actor,
    )
    audit(actor, "payment.verified", row.pk, method=method, amount=str(amount))
    return {"payment": row.pk, "receipt": str(row.receipt)}


@command("fee.exempt")
def exempt_fee(*, actor, application_id, reason):
    app = Application.objects.select_for_update().get(pk=application_id)
    if not reason.strip() or app.state != "submitted":
        raise ValidationError("Pending application and reason required")
    row = Exemption.objects.create(application=app, actor=actor, reason=reason)
    audit(actor, "fee.exempted", row.pk, reason)
    return {"exemption": row.pk}


def issue(
    kind,
    *,
    membership=None,
    accreditation=None,
    registration=None,
    version=1,
    replaces=None
):
    token = secrets.token_urlsafe(32)
    code = secrets.token_hex(8).upper()
    name = (
        membership.application.person.full_name
        if membership
        else (
            (
                accreditation.person.full_name
                if accreditation.person_id
                else accreditation.subject_name
            )
            if accreditation
            else registration.person.full_name
        )
    )
    doc = Document.objects.create(
        subject_name=name,
        kind=kind,
        membership=membership,
        accreditation=accreditation,
        registration=registration,
        version=version,
        replaces=replaces,
        token_digest=digest(token),
        code_digest=digest(code),
        credentials=encrypt({"token": token, "code": code}),
    )
    Outbox.objects.create(document=doc)
    return doc


@command("membership.approve")
def approve_membership(*, actor, application_id, reason):
    app = (
        Application.objects.select_for_update()
        .select_related("person", "previous")
        .get(pk=application_id)
    )
    if app.state != "submitted" or not reason.strip():
        raise Conflict("Pending application and approval reason required")
    paid = app.payment_set.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    refunded = Refund.objects.filter(payment__application=app, approved=True).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    if (
        paid - refunded < app.quote
        and not Exemption.objects.filter(application=app).exists()
    ):
        raise ValidationError("Verified payment or documented exemption required")
    starts = today()
    if app.previous_id:
        previous = Membership.objects.select_for_update().get(pk=app.previous_id)
        if previous.state not in {"active", "expired"} or previous.ends_on is None:
            raise ValidationError("Membership must be renewable")
        # Only one renewal chain per term; next renewal refers to the latest term.
        if Application.objects.filter(previous=previous, state="approved").exists():
            raise Conflict("This term has already been renewed")
        if previous.ends_on > starts:
            starts = previous.ends_on
    ends = None if app.tier in {"founder", "honorary"} else year_after(starts)
    membership = Membership.objects.create(
        application=app, starts_on=starts, ends_on=ends
    )
    documents = [
        issue(
            "gold_card" if app.tier == "accredited" else "membership_card",
            membership=membership,
        )
    ]
    if app.tier == "accredited":
        accreditation = Accreditation.objects.create(
            membership=membership, person=app.person, starts_on=starts, ends_on=ends
        )
        documents.append(issue("professional_certificate", accreditation=accreditation))
    app.state = "approved"
    app.save(update_fields=["state"])
    audit(
        actor,
        "membership.approved",
        membership.pk,
        reason,
        policy=POLICY_VERSION,
        tier=app.tier,
    )
    return {"membership": membership.pk, "documents": [x.pk for x in documents]}


@command("accreditation.approve")
def approve_accreditation(
    *, actor, kind, person_id, subject_name, starts_on, ends_on, reason
):
    start = date.fromisoformat(starts_on)
    end = date.fromisoformat(ends_on)
    if (
        kind not in {"individual", "institution", "course"}
        or not reason.strip()
        or end <= start
    ):
        raise ValidationError("Invalid independent accreditation")
    if kind != "course" and end != year_after(start):
        raise ValidationError("Individual/institution accreditation must last one year")
    if (
        kind == "individual"
        and not person_id
        or kind in {"institution", "course"}
        and (person_id or not subject_name.strip())
    ):
        raise ValidationError("Explicit accreditation subject required")
    person = Person.objects.get(pk=person_id) if person_id else None
    if person and person.verification_notice_at is None:
        raise ValidationError("Verification notice required")
    row = Accreditation.objects.create(
        kind=kind,
        person=person,
        subject_name=subject_name,
        starts_on=start,
        ends_on=end,
    )
    doc = issue("accreditation_certificate", accreditation=row)
    audit(actor, "accreditation.approved", row.pk, reason, policy=POLICY_VERSION)
    return {"accreditation": row.pk, "document": doc.pk}


@command("right.state")
def change_state(*, actor, model, object_id, state, reason):
    if (
        model not in {"membership", "accreditation"}
        or state not in {"active", "suspended", "cancelled"}
        or not reason.strip()
    ):
        raise ValidationError("Invalid right decision")
    cls = Membership if model == "membership" else Accreditation
    row = cls.objects.select_for_update().get(pk=object_id)
    row.state = state
    row.save(update_fields=["state"])
    if model == "membership":
        Accreditation.objects.filter(membership=row).update(state=state)
        # Keep future approved renewal terms consistent with parent decisions.
        parents = [row.pk]
        while parents:
            future = list(
                Membership.objects.select_for_update().filter(
                    application__previous_id__in=parents, starts_on__gte=today()
                )
            )
            parents = [term.pk for term in future]
            for term in future:
                term.state = state
                term.save(update_fields=["state"])
                Accreditation.objects.filter(membership=term).update(state=state)
    elif row.membership_id and row.membership.state != "active" and state == "active":
        raise ValidationError("Linked accreditation cannot outlive inactive membership")
    audit(actor, model + "." + state, row.pk, reason)
    return {"id": row.pk, "state": state}


@command("document.replace")
def replace_document(*, actor, document_id, reason):
    old = Document.objects.select_for_update().get(pk=document_id)
    if old.void or not reason.strip():
        raise Conflict("Valid original document and replacement reason required")
    new = issue(
        old.kind,
        membership=old.membership,
        accreditation=old.accreditation,
        registration=old.registration,
        version=old.version + 1,
        replaces=old,
    )
    old.void = True
    old.save(update_fields=["void"])
    audit(actor, "document.replaced", new.pk, reason, previous=old.pk)
    return {"document": new.pk}


@command("refund.decide")
def decide_refund(*, actor, payment_id, amount, approved, reason):
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    amount = money(amount)
    total = Refund.objects.filter(payment=payment, approved=True).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    if (
        not isinstance(approved, bool)
        or not reason.strip()
        or amount <= 0
        or (approved and total + amount > payment.amount)
    ):
        raise ValidationError("Invalid refund decision")
    row = Refund.objects.create(
        payment=payment, amount=amount, approved=approved, reason=reason, actor=actor
    )
    audit(
        actor, "refund.decided", row.pk, reason, approved=approved, amount=str(amount)
    )
    return {"refund": row.pk, "approved": approved}


def register(
    activity, person, user, *, guardian_name="", guardian_capacity="", consent=False
):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authenticated applicant required")
    if person.minor:
        if (
            person.guardian_id != user.pk
            or not activity.allows_minors
            or consent is not True
            or not guardian_name.strip()
            or not guardian_capacity.strip()
        ):
            raise ValidationError(
                "Eligible activity and legal guardian explicit consent required"
            )
    elif person.user_id != user.pk:
        raise PermissionDenied("Own participant profile required")
    if person.verification_notice_at is None:
        raise ValidationError("Verification notice acknowledgment required")
    with transaction.atomic():
        Person.objects.select_for_update().get(pk=person.pk)
        if Registration.objects.filter(activity=activity, person=person).exists():
            raise Conflict("Participant already registered")
        return Registration.objects.create(
            activity=activity,
            person=person,
            submitted_by=user,
            guardian_name=guardian_name if person.minor else "",
            guardian_capacity=guardian_capacity if person.minor else "",
            consent_at=timezone.now() if person.minor else None,
            consent_version=activity.consent_version if person.minor else "",
            consent_text=activity.consent_text if person.minor else "",
        )


@command("registration.decide")
def decide_registration(*, actor, registration_id, accept, reason):
    row = (
        Registration.objects.select_for_update()
        .select_related("activity", "person")
        .get(pk=registration_id)
    )
    activity = Activity.objects.select_for_update().get(pk=row.activity_id)
    if row.state != "requested" or not isinstance(accept, bool) or not reason.strip():
        raise Conflict("Pending registration and reason required")
    if accept:
        if row.person.minor and (
            not row.consent_at or not row.guardian_name or not activity.allows_minors
        ):
            raise ValidationError("Guardian consent required")
        if (
            Registration.objects.filter(activity=activity, state="confirmed").count()
            >= activity.capacity
        ):
            raise Conflict("Activity capacity reached")
        row.state = "confirmed"
        doc = issue("invitation", registration=row)
    else:
        row.state = "rejected"
        doc = None
    row.save(update_fields=["state"])
    audit(actor, "registration.decided", row.pk, reason, accepted=accept)
    return {"registration": row.pk, "document": doc.pk if doc else None}


@command("registration.cancel")
def cancel_registration(*, actor, registration_id, reason):
    row = Registration.objects.select_for_update().get(pk=registration_id)
    if row.state not in {"requested", "confirmed"} or not reason.strip():
        raise Conflict("Cancellable registration required")
    row.state = "cancelled"
    row.save(update_fields=["state"])
    audit(actor, "registration.cancelled", row.pk, reason)
    return {"registration": row.pk}


@command("attendance.checkin")
def check_in(*, actor, document_id):
    doc = (
        Document.objects.select_for_update()
        .select_related("registration")
        .get(pk=document_id)
    )
    if doc.kind != "invitation" or doc.void or document_status(doc) != "active":
        raise ValidationError("Valid confirmed invitation required")
    row, _ = Attendance.objects.get_or_create(
        registration=doc.registration, defaults={"actor": actor}
    )
    audit(actor, "attendance.checked", row.pk)
    return {"attendance": row.pk}


def document_status(doc):
    if doc.void:
        return "cancelled"
    if doc.membership_id:
        origin = doc.membership
    elif doc.accreditation_id:
        origin = doc.accreditation
        if origin.membership_id and origin.membership.state != "active":
            return origin.membership.state
    else:
        origin = doc.registration
        if origin.state != "confirmed":
            return "cancelled"
        return "expired" if today() > origin.activity.ends_on else "active"
    if origin.state != "active":
        return origin.state
    if origin.ends_on and today() >= origin.ends_on:
        return "expired"
    if today() < origin.starts_on:
        return "pending"  # early-renewal document not valid before its future start
    return "active"


def public_document(doc):
    if doc.membership_id:
        origin = doc.membership
        name = origin.application.person.full_name
        kind = origin.application.tier
    elif doc.accreditation_id:
        origin = doc.accreditation
        name = origin.person.full_name if origin.person_id else origin.subject_name
        kind = origin.kind
    else:
        origin = doc.registration
        name = origin.person.full_name
        kind = "activity invitation"
    start = origin.activity.starts_on if doc.registration_id else origin.starts_on
    end = origin.activity.ends_on if doc.registration_id else origin.ends_on
    return {
        "full_name": doc.subject_name,
        "type": kind,
        "document_type": doc.kind,
        "reference": str(doc.serial),
        "valid_from": str(start),
        "valid_until": str(end) if end else None,
        "status": document_status(doc),
    }


def lookup_document(*, token=None, serial=None, code=None):
    if token:
        doc = Document.objects.filter(token_digest=digest(token)).first()
    elif serial and code:
        try:
            doc = Document.objects.filter(
                serial=serial, code_digest=digest(code.strip().upper())
            ).first()
        except (ValidationError, ValueError):
            return None
    else:
        return None
    return public_document(doc) if doc else None
