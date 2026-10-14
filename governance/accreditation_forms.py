from django import forms
from .models import Person

class PrivateFields(forms.Form):
    key = forms.UUIDField(widget=forms.HiddenInput)
    criteria = forms.CharField(max_length=10000, required=False, widget=forms.Textarea)
    assessment = forms.CharField(max_length=10000, required=False, widget=forms.Textarea)
    fee = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2, required=False)
    reason = forms.CharField(max_length=3000, widget=forms.Textarea)
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = labels.get(name, field.label)
        for name in ("kind", "decision"):
            if name in self.fields:
                self.fields[name].choices = [(value, labels[value]) for value, _ in self.fields[name].choices]

class CaseForm(PrivateFields):
    kind = forms.ChoiceField(choices=[(x,x) for x in ("individual","institution","course")])
    person = forms.ModelChoiceField(queryset=Person.objects.none(), required=False)
    subject = forms.CharField(max_length=200, required=False)
    start = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
    end = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.filter(verification_notice_at__isnull=False).order_by("pk")
        self.fields["person"].label_from_instance = lambda obj: obj.full_name

class ReviewForm(PrivateFields):
    decision = forms.ChoiceField(choices=[(x,x) for x in ("draft","reviewed","rejected")])

class ApprovalForm(forms.Form):
    key = forms.UUIDField(widget=forms.HiddenInput)
    reason = forms.CharField(max_length=3000, widget=forms.Textarea)
    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].label = labels["reason"]
