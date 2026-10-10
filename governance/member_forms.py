import uuid
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
)
from .services import TIERS


def label_fields(form, labels):
    for name, field in form.fields.items():
        if name != "key":
            field.label = labels.get(name, name)


class SignupForm(UserCreationForm):
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        label_fields(self, labels)


class LoginForm(AuthenticationForm):
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        label_fields(self, labels)


class ChangePasswordForm(PasswordChangeForm):
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        label_fields(self, labels)


class CommandForm(forms.Form):
    key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        label_fields(self, labels)


class ProfileForm(CommandForm):
    full_name = forms.CharField(max_length=200)
    contact = forms.EmailField(required=False)
    directory_consent = forms.BooleanField(required=False)
    notice = forms.BooleanField(required=True)


class ApplicationForm(CommandForm):
    tier = forms.ChoiceField(choices=[])

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["tier"].choices = [(k, labels[k]) for k in TIERS]


class RenewalForm(CommandForm):
    membership_id = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, labels, user, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        from .models import Membership, Application

        self.fields["membership_id"].queryset = Membership.objects.filter(
            application__person__user=user,
            ends_on__isnull=False,
            state__in=["active", "expired"],
        ).exclude(
            pk__in=Application.objects.filter(
                state="approved", previous__isnull=False
            ).values("previous_id")
        )
        self.fields["membership_id"].label_from_instance = (
            lambda term: f"{term.pk} — {labels[term.application.tier]} — {term.starts_on} / {term.ends_on}"
        )
