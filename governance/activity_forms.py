from django import forms
from django.db.models import Q
from .models import Person

class LabelForm(forms.Form):
    def __init__(self,*args,labels,**kwargs):
        super().__init__(*args,**kwargs)
        for name,field in self.fields.items(): field.label=labels.get(name,field.label)

class ActivityForm(LabelForm):
    key=forms.UUIDField(widget=forms.HiddenInput)
    event_title=forms.CharField(max_length=200)
    starts_on=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
    ends_on=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
    capacity=forms.IntegerField(min_value=1,max_value=100000)
    allows_minors=forms.BooleanField(required=False)
    consent_version=forms.CharField(max_length=60,required=False)
    consent_text=forms.CharField(max_length=10000,required=False,widget=forms.Textarea)
    reason=forms.CharField(max_length=3000,widget=forms.Textarea)

class RegistrationForm(LabelForm):
    person=forms.ModelChoiceField(queryset=Person.objects.none())
    guardian_name=forms.CharField(max_length=200,required=False)
    guardian_capacity=forms.CharField(max_length=100,required=False)
    consent=forms.BooleanField(required=False)
    def __init__(self,*args,user,activity,**kwargs):
        super().__init__(*args,**kwargs)
        scope=Q(user=user,minor=False)
        if activity.allows_minors: scope |= Q(guardian=user,minor=True)
        self.fields['person'].queryset=Person.objects.filter(scope,verification_notice_at__isnull=False).order_by('pk')
        self.fields['person'].label_from_instance=lambda row:row.full_name

class DecisionForm(LabelForm):
    key=forms.UUIDField(widget=forms.HiddenInput)
    operation=forms.ChoiceField(choices=[(x,x) for x in ('accept','reject','cancel')])
    reason=forms.CharField(max_length=3000,widget=forms.Textarea)
    def __init__(self,*args,**kwargs):
        labels=kwargs['labels']; super().__init__(*args,**kwargs)
        self.fields['operation'].label=labels['decision']
        self.fields['operation'].choices=[(x,labels[x]) for x in ('accept','reject','cancel')]

class CheckinForm(forms.Form):
    key=forms.UUIDField(widget=forms.HiddenInput)
