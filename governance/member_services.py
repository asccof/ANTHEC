"""Self-service commands lock the authenticated account, never grant admin rights."""

from functools import wraps
import uuid
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from . import services as s
from .models import Person, Command, Application, Membership
from .intake import validate_capacity, validate_phone, validate_addresses


def member_command(action):
    def decorate(fn):
        @wraps(fn)
        def wrapped(user, *, key, **payload):
            from .deployment import require_applications_enabled
            if action == "member.profile":
                if (getattr(settings, "ANTHEEC_OWNER_TESTING", False) or
                        getattr(settings, "ANTHEEC_PUBLIC_PREVIEW", False)):
                    raise PermissionDenied("Profile updates are disabled in preview modes.")
            else:
                require_applications_enabled()
            if (
                not user.is_authenticated
                or not isinstance(key, str)
                or not key
                or len(key) > 120
            ):
                raise PermissionDenied("Authenticated account and command key required")
            with transaction.atomic():
                user = get_user_model().objects.select_for_update().get(pk=user.pk)
                if not user.is_active:
                    raise PermissionDenied("Inactive account")
                import json
                hashed = s.digest(json.dumps(payload, sort_keys=True, default=str))
                from .privacy_notice import pop_ack, record
                evidence = pop_ack(payload) if action in {'member.profile', 'member.application', 'member.renewal', 'portrait.upload'} else None
                previous = Command.objects.filter(
                    actor=user, action=action, key=key
                ).first()
                if previous:
                    if previous.digest != hashed:
                        raise s.Conflict("Key reused with different input")
                    return previous.result
                arguments = dict(payload)
                if action == 'member.application':
                    arguments['_privacy_evidence'] = evidence
                result = fn(user=user, **arguments)
                subject = next((result[name] for name in ('application', 'portrait', 'person') if name in result), user.pk)
                record(user, action, subject, evidence)
                Command.objects.create(
                    actor=user, action=action, key=key, digest=hashed, result=result
                )
                return result

        return wrapped

    return decorate


@member_command("member.profile")
def update_profile(
    *, user, full_name, contact, directory_consent, notice, phone=None, profession=None
):
    if (
        not isinstance(full_name, str)
        or not full_name.strip()
        or len(full_name) > 200
        or not isinstance(contact, str)
        or len(contact) > 254
        or not isinstance(directory_consent, bool)
        or notice is not True
    ):
        raise ValidationError("Profile and explicit verification notice required")
    if phone is not None:
        validate_phone(phone)
    if profession is not None and (
        not isinstance(profession, str)
        or not profession.strip()
        or len(profession) > 200
    ):
        raise ValidationError("Profession or field of study required")
    person, created = Person.objects.get_or_create(
        user=user, defaults={"full_name": full_name.strip()}
    )
    # Administrative minor/guardian identity cannot be overwritten by self-service.
    if person.minor or person.guardian_id:
        raise PermissionDenied("Managed identity requires administrative correction")
    person.full_name = full_name.strip()
    person.contact = contact
    if phone is not None:
        person.phone = phone.strip()
    if profession is not None:
        person.profession = profession.strip()
    person.directory_consent = directory_consent
    if person.verification_notice_at is None:
        person.verification_notice_at = timezone.now()
    person.save(
        update_fields=[
            "full_name",
            "contact",
            "phone",
            "profession",
            "directory_consent",
            "verification_notice_at",
        ]
    )
    s.audit(
        user,
        "member.profile.created" if created else "member.profile.updated",
        person.pk,
        notice_version="verification-v1",
        directory_consent=directory_consent,
    )
    return {"person": person.pk}


@member_command("member.application")
def submit_application(
    *,
    user,
    tier,
    applicant_capacity,
    capacity_other="",
    address_category,
    correspondence_address="",
    professional_address="",
    residential_address="",
    same_address=False,
    image_data,
    photo_consent,
    _privacy_evidence=None
):
    (
        address_category,
        correspondence_address,
        professional_address,
        residential_address,
    ) = validate_addresses(
        address_category,
        correspondence_address,
        professional_address,
        residential_address,
        same_address,
    )

    applicant_capacity, capacity_other = validate_capacity(
        applicant_capacity, capacity_other
    )
    person = Person.objects.select_for_update().get(user=user)
    validate_phone(person.phone)
    if not person.profession.strip():
        raise ValidationError("Complete the private profile before applying")
    if person.minor or person.guardian_id:
        raise PermissionDenied("Managed membership requires administrative review")
    if Application.objects.filter(person=person, state="submitted").exists():
        raise s.Conflict("Pending application already exists")
    if Membership.objects.filter(application__person=person).exists():
        raise s.Conflict("Use renewal of existing membership")
    from . import portraits

    result = portraits.upload_portrait(
        user,
        key="intake-" + str(uuid.uuid4()),
        person_id=person.pk,
        image_data=image_data,
        consent=photo_consent,
        **({'privacy_acceptance': True, 'privacy_version': _privacy_evidence['version'],
            'privacy_language': _privacy_evidence['language']} if _privacy_evidence else {}),
    )
    from .models import Portrait

    photo = Portrait.objects.get(serial=result["portrait"])
    app = s.create_application(person, tier)
    app.intake_version = 1
    app.intake_portrait = photo
    app.address_category = address_category
    app.correspondence_address = correspondence_address
    app.professional_address = professional_address
    app.residential_address = residential_address
    app.applicant_capacity = applicant_capacity
    app.capacity_other = capacity_other
    app.profession_snapshot = person.profession
    app.save(
        update_fields=[
            "applicant_capacity",
            "capacity_other",
            "profession_snapshot",
            "intake_version",
            "intake_portrait",
            "address_category",
            "correspondence_address",
            "professional_address",
            "residential_address",
        ]
    )
    s.audit(
        user,
        "member.application.submitted",
        app.pk,
        tier=tier,
        applicant_capacity=applicant_capacity,
    )
    return {"application": app.pk}


@member_command("member.renewal")
def submit_renewal(*, user, membership_id):
    if (
        not isinstance(membership_id, int)
        or isinstance(membership_id, bool)
        or membership_id <= 0
    ):
        raise ValidationError("Membership identifier required")
    person = Person.objects.select_for_update().get(user=user)
    if person.minor or person.guardian_id:
        raise PermissionDenied("Managed membership requires administrative review")
    previous = Membership.objects.select_for_update().get(
        pk=membership_id, application__person=person
    )
    if previous.ends_on is None or previous.state not in {"active", "expired"}:
        raise s.Conflict("Membership not renewable")
    if Application.objects.filter(person=person, state="submitted").exists():
        raise s.Conflict("Pending application already exists")
    if Application.objects.filter(previous=previous, state="approved").exists():
        raise s.Conflict("Select latest approved term")
    app = s.create_application(person, previous.application.tier, previous=previous)
    app.applicant_capacity = previous.application.applicant_capacity
    app.capacity_other = previous.application.capacity_other
    app.profession_snapshot = person.profession
    app.save(
        update_fields=["applicant_capacity", "capacity_other", "profession_snapshot"]
    )
    s.audit(
        user, "member.renewal.submitted", app.pk, previous=previous.pk, tier=app.tier
    )
    return {"application": app.pk}
