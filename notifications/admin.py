from django.contrib import admin
from .models import ChannelProvider, MessageTemplate, Notification, SMSLog


@admin.register(ChannelProvider)
class ChannelProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'provider_type', 'is_active', 'is_default']
    list_filter = ['channel', 'provider_type', 'is_active', 'is_default']


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'is_active']
    list_filter = ['channel', 'is_active']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'channel', 'status', 'created_at']
    list_filter = ['channel', 'status']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['to_number', 'status', 'sid', 'created_at']
    list_filter = ['status']
