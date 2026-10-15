from django import forms
from django.contrib.auth import get_user_model
from .models import Authority

class DecisionFields(forms.Form):
    key = forms.UUIDField(widget=forms.HiddenInput)
    reason = forms.CharField(max_length=3000, widget=forms.Textarea)
    confirm = forms.BooleanField()
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = labels.get(name, field.label)

class DirectorForm(DecisionFields):
    user = forms.ModelChoiceField(queryset=get_user_model().objects.none())
    decision = forms.ChoiceField(choices=[("grant", "grant"), ("revoke", "revoke")])
    def __init__(self, *args, **kwargs):
        labels = kwargs["labels"]
        super().__init__(*args, **kwargs)
        primary = Authority.objects.get(pk=1).primary_id
        self.fields["user"].queryset = get_user_model().objects.filter(is_superuser=False).exclude(pk=primary).order_by("pk")
        self.fields["user"].label_from_instance = lambda user: user.get_username()
        self.fields["decision"].choices = [(key, labels[key]) for key in ("grant", "revoke")]

class PriceForm(DecisionFields):
    tier = forms.ChoiceField(choices=[(key, key) for key in ("general", "affiliate", "advanced", "accredited")])
    amount = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)
    starts_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"))
    def __init__(self, *args, **kwargs):
        labels = kwargs["labels"]
        super().__init__(*args, **kwargs)
        self.fields["tier"].choices = [(key, labels[key]) for key in ("general", "affiliate", "advanced", "accredited")]
