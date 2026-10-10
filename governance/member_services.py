"""Self-service commands lock the authenticated account, never grant admin rights."""

from functools import wraps
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from . import services as s
from .models import Person, Command, Application, Membership


def member_command(action):
    def decorate(fn):
        @wraps(fn)
        def wrapped(user, *, key, **payload):
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
                previous = Command.objects.filter(
                    actor=user, action=action, key=key
                ).first()
                if previous:
                    if previous.digest != hashed:
                        raise s.Conflict("Key reused with different input")
                    return previous.result
                result = fn(user=user, **payload)
                Command.objects.create(
                    actor=user, action=action, key=key, digest=hashed, result=result
                )
                return result

        return wrapped

    return decorate


@member_command("member.profile")
def update_profile(*, user, full_name, contact, directory_consent, notice):
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
    person, created = Person.objects.get_or_create(
        user=user, defaults={"full_name": full_name.strip()}
    )
    # Administrative minor/guardian identity cannot be overwritten by self-service.
    if person.minor or person.guardian_id:
        raise PermissionDenied("Managed identity requires administrative correction")
    person.full_name = full_name.strip()
    person.contact = contact
    person.directory_consent = directory_consent
    if person.verification_notice_at is None:
        person.verification_notice_at = timezone.now()
    person.save(
        update_fields=[
            "full_name",
            "contact",
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
def submit_application(*, user, tier):
    person = Person.objects.select_for_update().get(user=user)
    if person.minor or person.guardian_id:
        raise PermissionDenied("Managed membership requires administrative review")
    if Application.objects.filter(person=person, state="submitted").exists():
        raise s.Conflict("Pending application already exists")
    if Membership.objects.filter(application__person=person).exists():
        raise s.Conflict("Use renewal of existing membership")
    app = s.create_application(person, tier)
    s.audit(user, "member.application.submitted", app.pk, tier=tier)
    return {"application": app.pk}
