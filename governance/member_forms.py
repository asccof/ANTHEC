import uuid
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
)
from .services import TIERS
from .intake import CAPACITIES, validate_capacity, validate_phone, validate_addresses
from .privacy_notice import PrivacyNoticeMixin


def label_fields(form, labels):
    for name, field in form.fields.items():
        if name != "key" and not name.startswith('privacy_'):
            field.label = labels.get(name, name)


class SignupForm(PrivacyNoticeMixin, UserCreationForm):
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


class ProfileForm(PrivacyNoticeMixin, CommandForm):
    full_name = forms.CharField(max_length=200)
    contact = forms.EmailField(required=False)
    phone = forms.CharField(max_length=32, validators=[validate_phone])
    profession = forms.CharField(max_length=200)
    directory_consent = forms.BooleanField(required=False)
    notice = forms.BooleanField(required=True)


class ApplicationForm(PrivacyNoticeMixin, CommandForm):
    address_category = forms.ChoiceField(choices=[])
    correspondence_address = forms.CharField(
        max_length=1000, required=False, widget=forms.Textarea
    )
    same_address = forms.BooleanField(required=False)
    professional_address = forms.CharField(
        max_length=1000, required=False, widget=forms.Textarea
    )
    residential_address = forms.CharField(
        max_length=1000, required=False, widget=forms.Textarea
    )
    photo = forms.FileField()
    photo_consent = forms.BooleanField()

    tier = forms.ChoiceField(choices=[])
    applicant_capacity = forms.ChoiceField(choices=[])
    capacity_other = forms.CharField(max_length=200, required=False)

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["tier"].choices = [(k, labels[k]) for k in TIERS]
        self.labels = labels
        self.fields["address_category"].choices = [("", "---------")] + [
            (k, labels["address_" + k]) for k in ("professional", "beneficiary")
        ]
        from .portrait_labels import LABELS

        photo_labels = next(v for v in LABELS.values() if v["photo"] == labels["photo"])
        self.fields["photo"].help_text = (
            photo_labels["notice"] + " " + labels["intake_photo_notice"]
        )
        self.fields["photo_consent"].label = photo_labels["consent"]
        self.fields["applicant_capacity"].choices = [("", "---------")] + [
            (k, labels["capacity_option_other" if k == "other" else "capacity_" + k])
            for k in CAPACITIES
        ]
        self.fields["applicant_capacity"].help_text = labels["capacity_notice"]
        self.fields["capacity_other"].help_text = labels["capacity_other_hint"]

    def clean(self):
        data = super().clean()
        if data.get("applicant_capacity"):
            try:
                validate_capacity(
                    data["applicant_capacity"], data.get("capacity_other", "")
                )
            except forms.ValidationError:
                self.add_error("capacity_other", self.labels["capacity_other_hint"])
        if data.get("address_category"):
            try:
                validate_addresses(
                    data["address_category"],
                    data.get("correspondence_address", ""),
                    data.get("professional_address", ""),
                    data.get("residential_address", ""),
                    data.get("same_address", False),
                )
            except forms.ValidationError:
                self.add_error(None, self.labels["address_required"])
        return data


class RenewalForm(PrivacyNoticeMixin, CommandForm):
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
