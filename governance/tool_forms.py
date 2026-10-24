import uuid
from urllib.parse import urlsplit
from django import forms
from django.core import signing
from django.core.validators import URLValidator
from .models import MemberTool
from .intake import validate_phone
from .member_forms import CommandForm, label_fields
from .privacy_notice import PrivacyNoticeMixin
from .activity_editorial import normalize_image, MAX_INPUT


class ToolForm(forms.ModelForm):
    key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    image_file = forms.FileField(required=False)
    remove_image = forms.BooleanField(required=False)

    class Meta:
        model = MemberTool
        fields = [field+'_'+language for language in ('ar','fr','en')
                  for field in ('title','summary','description')] + ['website','sort_order','published']
        widgets = {field+'_'+lang: forms.Textarea(attrs={'rows': 5 if field == 'description' else 2})
                   for lang in ('ar','fr','en') for field in ('summary','description')}

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, **kwargs)
        label_fields(self, labels)
        self.fields['image_file'].help_text = labels['image_notice']
        for name in self.fields:
            if name.endswith(('_ar','_fr','_en')):
                self.fields[name].widget.attrs.update(lang=name[-2:], dir='rtl' if name.endswith('_ar') else 'ltr')

    def clean_website(self):
        url = self.cleaned_data['website']
        if url:
            URLValidator(schemes=['https'])(url)
            if urlsplit(url).username or urlsplit(url).password:
                raise forms.ValidationError('Credentials are not allowed in public links.')
        return url

    def clean_image_file(self):
        upload = self.cleaned_data.get('image_file')
        if upload:
            if upload.size > MAX_INPUT:
                raise forms.ValidationError('Maximum 3 MiB.')
            self.normalized_image = normalize_image(upload.read(MAX_INPUT+1))
        else:
            self.normalized_image = None
        return upload

    def clean(self):
        data = super().clean()
        if data.get('remove_image') and data.get('image_file'):
            self.add_error('image_file', 'Choose replacement or removal, not both.')
        return data


class ToolRequestForm(PrivacyNoticeMixin, forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)
    full_name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=32, validators=[validate_phone])
    email = forms.EmailField(max_length=254)

    def __init__(self, *args, labels, tool_id, **kwargs):
        self.tool_id = tool_id
        super().__init__(*args, **kwargs)
        label_fields(self, labels)
        self.fields['token'].initial = signing.dumps({'tool':tool_id,'nonce':str(uuid.uuid4())}, salt='tool-request')
        self.fields['full_name'].widget.attrs['autocomplete'] = 'name'
        self.fields['phone'].widget.attrs.update(autocomplete='tel', type='tel')
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    def clean_token(self):
        try:
            value = signing.loads(self.cleaned_data['token'], salt='tool-request', max_age=14400)
            if value['tool'] != self.tool_id:
                raise ValueError()
            return uuid.UUID(value['nonce'])
        except (signing.BadSignature, KeyError, TypeError, ValueError):
            raise forms.ValidationError('Reopen this form and try again.') from None


class ToolReviewForm(CommandForm):
    state = forms.ChoiceField(choices=[])
    notes = forms.CharField(required=False, max_length=3000, widget=forms.Textarea)

    def __init__(self, *args, labels, **kwargs):
        super().__init__(*args, labels=labels, **kwargs)
        self.fields['state'].choices = [(key, labels[key]) for key in ('submitted','contacted','closed')]
