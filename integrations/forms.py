from django import forms
from .models import Integration, IntegrationConfig


class IntegrationForm(forms.ModelForm):
    class Meta:
        model = Integration
        fields = ['name', 'provider_code', 'category', 'description', 'documentation_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'provider_code': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'documentation_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def clean_provider_code(self):
        return self.cleaned_data.get('provider_code', '').strip().lower()


class IntegrationConfigForm(forms.ModelForm):
    api_key = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    token = forms.CharField(
        required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    client_id = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    client_secret = forms.CharField(
        required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    access_token = forms.CharField(
        required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    refresh_token = forms.CharField(
        required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    custom_config = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6})
    )
    webhook_url = forms.URLField(
        required=False, widget=forms.URLInput(attrs={'class': 'form-control'})
    )
    webhook_secret = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = IntegrationConfig
        fields = ['name', 'environment', 'auth_type', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'environment': forms.Select(attrs={'class': 'form-control'}),
            'auth_type': forms.Select(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            creds = self.instance.credentials or {}
            conf = self.instance.config or {}
            self.initial['api_key'] = creds.get('api_key', '')
            self.initial['username'] = creds.get('username', '')
            self.initial['password'] = creds.get('password', '')
            self.initial['token'] = creds.get('token', '')
            self.initial['client_id'] = creds.get('client_id', '')
            self.initial['client_secret'] = creds.get('client_secret', '')
            self.initial['access_token'] = creds.get('access_token', '')
            self.initial['refresh_token'] = creds.get('refresh_token', '')
            self.initial['custom_config'] = creds.get('custom_config', '')
            self.initial['webhook_url'] = conf.get('webhook_url', '')
            self.initial['webhook_secret'] = conf.get('webhook_secret', '')

    def clean_custom_config(self):
        value = self.cleaned_data.get('custom_config', '')
        if value:
            import json
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise forms.ValidationError('Invalid JSON format')
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        credentials = {}
        if self.cleaned_data.get('api_key'):
            credentials['api_key'] = self.cleaned_data['api_key']
        if self.cleaned_data.get('username'):
            credentials['username'] = self.cleaned_data['username']
        if self.cleaned_data.get('password'):
            credentials['password'] = self.cleaned_data['password']
        if self.cleaned_data.get('token'):
            credentials['token'] = self.cleaned_data['token']
        if self.cleaned_data.get('client_id'):
            credentials['client_id'] = self.cleaned_data['client_id']
        if self.cleaned_data.get('client_secret'):
            credentials['client_secret'] = self.cleaned_data['client_secret']
        if self.cleaned_data.get('access_token'):
            credentials['access_token'] = self.cleaned_data['access_token']
        if self.cleaned_data.get('refresh_token'):
            credentials['refresh_token'] = self.cleaned_data['refresh_token']
        if self.cleaned_data.get('custom_config'):
            credentials['custom_config'] = self.cleaned_data['custom_config']
        instance.credentials = credentials

        config = {}
        if self.cleaned_data.get('webhook_url'):
            config['webhook_url'] = self.cleaned_data['webhook_url']
        if self.cleaned_data.get('webhook_secret'):
            config['webhook_secret'] = self.cleaned_data['webhook_secret']
        instance.config = config

        if commit:
            instance.save()
        return instance
