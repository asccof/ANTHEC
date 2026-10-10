from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from . import services as s
from .models import Application, Person


@s.command("membership.reject")
def reject(*, actor, application_id, reason):
    app = Application.objects.select_for_update().get(pk=application_id)
    if app.state != "submitted" or not reason.strip():
        raise s.Conflict("Submitted application and reason required")
    app.state = "rejected"
    app.save(update_fields=["state"])
    s.audit(actor, "membership.rejected", app.pk, reason)
    return {"application": app.pk, "state": app.state}


@s.command("person.link")
def link_person(*, actor, person_id, user_id, reason):
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    person = Person.objects.select_for_update().get(pk=person_id)
    if (
        not reason.strip()
        or not user.is_active
        or person.user_id
        or person.minor
        or person.guardian_id
        or Person.objects.filter(user=user).exists()
    ):
        raise s.Conflict("Unlinked adult record and unlinked active account required")
    person.user = user
    person.save(update_fields=["user"])
    s.audit(actor, "person.linked", person.pk, reason, user_id=user.pk)
    return {"person": person.pk, "user": user.pk}
