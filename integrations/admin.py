from django.contrib import admin
from .models import Integration, IntegrationConfig, IntegrationLog


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_code', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'provider_code']
    readonly_fields = ['created_at']


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'integration', 'auth_type', 'environment', 'is_default', 'is_active', 'created_at']
    list_filter = ['auth_type', 'environment', 'is_default', 'is_active']
    search_fields = ['name', 'integration__name']
    readonly_fields = ['created_at']


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'config', 'method', 'status_code', 'is_success', 'duration_ms', 'created_at']
    list_filter = ['method', 'is_success']
    search_fields = ['action', 'endpoint', 'error_message']
    readonly_fields = ['created_at']
