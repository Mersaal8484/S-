from django.db import models


class Integration(models.Model):
    class Category(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        COMMUNICATION = 'COMMUNICATION', 'Communication'
        CRM = 'CRM', 'CRM'
        ACCOUNTING = 'ACCOUNTING', 'Accounting'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=200)
    provider_code = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True, default='')
    documentation_url = models.URLField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class IntegrationConfig(models.Model):
    class AuthType(models.TextChoices):
        API_KEY = 'API_KEY', 'API Key'
        BASIC_AUTH = 'BASIC_AUTH', 'Basic Auth'
        BEARER_TOKEN = 'BEARER_TOKEN', 'Bearer Token'
        OAUTH2 = 'OAUTH2', 'OAuth2'
        CUSTOM = 'CUSTOM', 'Custom JSON'

    class Environment(models.TextChoices):
        SANDBOX = 'SANDBOX', 'Sandbox'
        LIVE = 'LIVE', 'Live'

    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='configs')
    name = models.CharField(max_length=200)
    auth_type = models.CharField(max_length=20, choices=AuthType.choices, default=AuthType.API_KEY)
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.SANDBOX)
    credentials = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)
    base_url = models.URLField(max_length=500, blank=True, default='')
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.integration.name} - {self.name}"


class IntegrationLog(models.Model):
    class Method(models.TextChoices):
        GET = 'GET', 'GET'
        POST = 'POST', 'POST'
        PUT = 'PUT', 'PUT'
        PATCH = 'PATCH', 'PATCH'
        DELETE = 'DELETE', 'DELETE'

    config = models.ForeignKey(IntegrationConfig, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=200)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.GET)
    endpoint = models.CharField(max_length=500, blank=True, default='')
    request_headers = models.JSONField(default=dict, blank=True)
    request_body = models.TextField(blank=True, default='')
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default='')
    is_success = models.BooleanField(default=True)
    duration_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.created_at}"
