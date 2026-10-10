from django import forms
from django.contrib.auth import get_user_model
from .member_forms import CommandForm
from .models import Person


class ReasonForm(CommandForm):
    reason = forms.CharField(max_length=4000, widget=forms.Textarea)


class PaymentForm(CommandForm):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(choices=[])
    proof_reference = forms.CharField(max_length=120)

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["method"].choices = [(k, labels[k]) for k in ("cash", "transfer")]


class RefundForm(ReasonForm):
    payment_id = forms.ModelChoiceField(queryset=None)
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    approved = forms.ChoiceField(choices=[])

    def __init__(self, *args, labels, payments, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["payment_id"].queryset = payments
        self.fields["payment_id"].label_from_instance = (
            lambda p: f"{p.receipt} — {p.amount}"
        )
        self.fields["approved"].choices = [
            ("yes", labels["approve"]),
            ("no", labels["reject"]),
        ]


class StateForm(ReasonForm):
    state = forms.ChoiceField(choices=[])

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["state"].choices = [
            (k, labels[k]) for k in ("active", "suspended", "cancelled")
        ]


class DocumentForm(ReasonForm):
    document_id = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, labels, documents, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["document_id"].queryset = documents.filter(void=False)
        self.fields["document_id"].label_from_instance = lambda doc: str(doc.serial)


class LinkForm(ReasonForm):
    person_id = forms.ModelChoiceField(queryset=Person.objects.none())
    user_id = forms.ModelChoiceField(queryset=get_user_model().objects.none())

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields["person_id"].queryset = Person.objects.filter(
            user=None, guardian=None, minor=False
        )
        self.fields["person_id"].label_from_instance = (
            lambda p: f"{p.pk} — {p.full_name}"
        )
        self.fields["user_id"].queryset = get_user_model().objects.filter(
            is_active=True, person__isnull=True
        )
