from django.db import models


class ChannelProvider(models.Model):
    class Channel(models.TextChoices):
        SMS = 'SMS', 'SMS'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push Notification'

    class ProviderType(models.TextChoices):
        MOCK = 'MOCK', 'Mock (Testing)'
        TWILIO = 'TWILIO', 'Twilio'
        WHATSAPP_API = 'WHATSAPP_API', 'WhatsApp API'
        FCM = 'FCM', 'Firebase Cloud Messaging'
        SMTP = 'SMTP', 'SMTP'

    name = models.CharField(max_length=100)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices)
    api_key = models.CharField(max_length=255, blank=True, default='')
    api_secret = models.CharField(max_length=255, blank=True, default='')
    sender_id = models.CharField(max_length=100, blank=True, default='')
    account_sid = models.CharField(max_length=255, blank=True, default='')
    auth_token = models.CharField(max_length=255, blank=True, default='')
    from_number = models.CharField(max_length=50, blank=True, default='')
    phone_number_id = models.CharField(max_length=100, blank=True, default='')
    access_token = models.CharField(max_length=255, blank=True, default='')
    fcm_credentials = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Channel Provider'
        verbose_name_plural = 'Channel Providers'
        ordering = ['-is_default', 'name']

    def __str__(self):
        return self.name


class MessageTemplate(models.Model):
    class Channel(models.TextChoices):
        SMS = 'SMS', 'SMS'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push Notification'

    name = models.CharField(max_length=100)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    variables = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'
        ordering = ['name']

    def __str__(self):
        return self.name


class Notification(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    class Channel(models.TextChoices):
        SMS = 'SMS', 'SMS'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push Notification'

    title = models.CharField(max_length=200)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    recipient = models.CharField(max_length=200)
    recipient_phone = models.CharField(max_length=50, blank=True, null=True)
    recipient_email = models.EmailField(blank=True, null=True)
    recipient_fcm_token = models.TextField(blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.ForeignKey(ChannelProvider, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SMSLog(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='sms_logs')
    to_number = models.CharField(max_length=50)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    sid = models.CharField(max_length=255, blank=True, default='')
    provider = models.ForeignKey(ChannelProvider, on_delete=models.SET_NULL, null=True, blank=True)
    provider_response_code = models.CharField(max_length=50, blank=True, default='')
    provider_response_message = models.TextField(blank=True, default='')
    delivery_status = models.CharField(max_length=50, blank=True, default='')
    delivery_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SMS Log'
        verbose_name_plural = 'SMS Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.to_number} - {self.status}"
