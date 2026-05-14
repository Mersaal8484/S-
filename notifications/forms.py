from django import forms
from .models import ChannelProvider, MessageTemplate, Notification


class ChannelProviderForm(forms.ModelForm):
    class Meta:
        model = ChannelProvider
        fields = ['name', 'channel', 'provider_type', 'api_key', 'api_secret',
                  'sender_id', 'account_sid', 'auth_token', 'from_number',
                  'phone_number_id', 'access_token', 'fcm_credentials',
                  'is_active', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'channel': forms.Select(attrs={'class': 'form-control'}),
            'provider_type': forms.Select(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'sender_id': forms.TextInput(attrs={'class': 'form-control'}),
            'account_sid': forms.TextInput(attrs={'class': 'form-control'}),
            'auth_token': forms.PasswordInput(attrs={'class': 'form-control'}),
            'from_number': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number_id': forms.TextInput(attrs={'class': 'form-control'}),
            'access_token': forms.PasswordInput(attrs={'class': 'form-control'}),
            'fcm_credentials': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['api_key', 'api_secret', 'sender_id', 'account_sid',
                      'auth_token', 'from_number', 'phone_number_id',
                      'access_token', 'fcm_credentials']:
            self.fields[field].required = False


class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ['name', 'channel', 'subject', 'body', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'channel': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].required = False

    def clean_variables(self):
        import re
        body = self.cleaned_data.get('body', '')
        if body:
            found = re.findall(r'\{(\w+)\}', body)
            return list(dict.fromkeys(found))
        return []


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'channel', 'recipient', 'recipient_phone',
                  'recipient_email', 'recipient_fcm_token', 'subject',
                  'body', 'template', 'provider']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'channel': forms.Select(attrs={'class': 'form-control'}),
            'recipient': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'recipient_fcm_token': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'template': forms.Select(attrs={'class': 'form-control'}),
            'provider': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient_phone'].required = False
        self.fields['recipient_email'].required = False
        self.fields['recipient_fcm_token'].required = False
        self.fields['subject'].required = False
        self.fields['template'].required = False
        self.fields['provider'].required = False
        self.fields['template'].queryset = MessageTemplate.objects.filter(is_active=True)
        self.fields['provider'].queryset = ChannelProvider.objects.filter(is_active=True)
