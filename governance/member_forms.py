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
