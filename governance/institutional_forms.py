from django import forms
from .models import Person, InstitutionalRole


class GrantForm(forms.Form):
    person_id = forms.ModelChoiceField(queryset=Person.objects.none())
    role = forms.ChoiceField(choices=[])
    starts_on = forms.DateField(
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    ends_on = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    legal_reference = forms.CharField(max_length=120)
    reason = forms.CharField(max_length=4000, widget=forms.Textarea)
    replaces_role_id = forms.ModelChoiceField(
        queryset=InstitutionalRole.objects.none(), required=False
    )
    key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person_id"].queryset = Person.objects.order_by("pk")
        self.fields["role"].choices = [
            (role, labels[role]) for role in ["president", "vice_president", "founder", "honorary"]
        ]
        self.fields["replaces_role_id"].queryset = InstitutionalRole.objects.filter(
            role__in=["president", "vice_president"], state__in=["active", "suspended"]
        ).order_by("pk")
        for name, field in self.fields.items():
            if name != "key":
                field.label = labels.get(
                    "person" if name == "person_id" else name, name
                )
        self.fields["person_id"].label_from_instance = (
            lambda person: f"{person.pk} — {person.full_name}"
        )
        self.fields["replaces_role_id"].label_from_instance = (
            lambda row: f"{row.pk} — {labels[row.role]} — {row.person.full_name} ({row.starts_on} / {row.ends_on})"
        )


class DecisionForm(forms.Form):
    state = forms.ChoiceField(choices=[])
    reason = forms.CharField(max_length=4000, widget=forms.Textarea)
    key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, labels, founder=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["state"].choices = [
            (state, labels[state])
            for state in (
                ["active", "suspended", "cancelled"]
                if founder
                else ["active", "suspended", "cancelled", "terminated"]
            )
        ]
        for name in ["state", "reason"]:
            self.fields[name].label = labels[name]


class ReplacementForm(forms.Form):
    document_id = forms.ModelChoiceField(queryset=None)
    reason = forms.CharField(max_length=4000, widget=forms.Textarea)
    key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, labels, documents, **kwargs):
        # Queryset assigned before rendering/validation; only this record's cards.
        super().__init__(*args, **kwargs)
        self.fields["document_id"].queryset = documents.filter(void=False)
        self.fields["document_id"].label_from_instance = lambda doc: str(doc.serial)
        self.fields["document_id"].label = labels["reference"]
        self.fields["reason"].label = labels["reason"]
