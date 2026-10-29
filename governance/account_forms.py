from django import forms
from django.contrib.auth import get_user_model
from .intake import validate_phone
from .models import Person


class AccountEditForm(forms.Form):
    username=forms.CharField(max_length=150,validators=get_user_model()._meta.get_field('username').validators)
    email=forms.EmailField(required=False,max_length=254)
    first_name=forms.CharField(required=False,max_length=150)
    last_name=forms.CharField(required=False,max_length=150)
    full_name=forms.CharField(required=False,max_length=200)
    contact=forms.EmailField(required=False,max_length=254)
    phone=forms.CharField(required=False,max_length=32)
    profession=forms.CharField(required=False,max_length=200)

    def __init__(self,*args,user,labels=None,**kwargs):
        self.user=user
        person=Person.objects.filter(user=user).first()
        initial={name:getattr(user,name) for name in ('username','email','first_name','last_name')}
        if person:
            initial.update({name:getattr(person,name) for name in ('full_name','contact','phone','profession')})
        super().__init__(*args,initial=initial,**kwargs)
        self.fields['full_name'].required=bool(person)
        if not person:
            for name in ('full_name','contact','phone','profession'):del self.fields[name]
        if labels:
            for name,field in self.fields.items():
                field.label=labels.get({'email':'account_email','first_name':'account_first_name','last_name':'account_last_name'}.get(name,name),name)

    def clean_username(self):
        value=get_user_model().normalize_username(self.cleaned_data['username'])
        if get_user_model().objects.exclude(pk=self.user.pk).filter(username=value).exists():
            raise forms.ValidationError('Username already exists')
        return value

    def clean_phone(self):
        value=self.cleaned_data.get('phone','')
        if value:validate_phone(value)
        return value


class AccountConfirmationForm(forms.Form):
    key=forms.UUIDField(widget=forms.HiddenInput)
    expected_epoch=forms.IntegerField(min_value=0,widget=forms.HiddenInput)
    confirm=forms.BooleanField(required=True)
    reason=forms.CharField(required=False,max_length=3000,widget=forms.Textarea(attrs={'rows':2}))

    def __init__(self,*args,labels,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['confirm'].label=labels['account_confirm']
        self.fields['reason'].label=labels['account_reason']
