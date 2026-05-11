from django.contrib import admin
from .models import Plan, Tenant, Domain


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'max_customers', 'max_meters', 'is_active']
    list_filter = ['tier', 'is_active']
    search_fields = ['name']


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'schema_name', 'plan', 'subscription_status', 'is_active', 'created_on']
    list_filter = ['subscription_status', 'is_active', 'plan', 'country']
    search_fields = ['company_name', 'schema_name', 'email']
    readonly_fields = ['schema_name', 'created_on']


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__company_name']
