from django import forms
from .member_forms import CommandForm
from .privacy_notice import PrivacyNoticeMixin

class PartnershipForm(PrivacyNoticeMixin, forms.Form):
    organization=forms.CharField(max_length=200)
    contact_email=forms.EmailField()
    message=forms.CharField(max_length=3000,widget=forms.Textarea)
    notice_acknowledged=forms.BooleanField(required=True)
    def __init__(self,*args,labels,**kwargs):
        super().__init__(*args,**kwargs)
        for name,field in self.fields.items():
            if not name.startswith('privacy_'): field.label=labels[name]

class PartnershipDecisionForm(CommandForm):
    decision=forms.ChoiceField(choices=[])
    reason=forms.CharField(max_length=4000,widget=forms.Textarea)
    def __init__(self,*args,labels,**kwargs):
        super().__init__(*args,labels=labels,**kwargs)
        self.fields['decision'].choices=[(v,labels[v]) for v in ['approved','rejected']]

class PartnerForm(CommandForm):
    name_ar=forms.CharField(max_length=200)
    name_fr=forms.CharField(max_length=200)
    name_en=forms.CharField(max_length=200)
    summary_ar=forms.CharField(required=False,max_length=3000,widget=forms.Textarea)
    summary_fr=forms.CharField(required=False,max_length=3000,widget=forms.Textarea)
    summary_en=forms.CharField(required=False,max_length=3000,widget=forms.Textarea)
    website=forms.URLField(required=False,max_length=200)
    state=forms.ChoiceField(choices=[])
    public_visible=forms.BooleanField(required=False)
    reason=forms.CharField(max_length=4000,widget=forms.Textarea)
    def __init__(self,*args,labels,**kwargs):
        super().__init__(*args,labels=labels,**kwargs)
        self.fields['state'].choices=[(v,labels[v]) for v in ['active','suspended','cancelled']]
