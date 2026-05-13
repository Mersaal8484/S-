from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Plan, Tenant, Domain


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'max_customers', 'max_meters', 'is_active']
    list_filter = ['tier', 'is_active']
    search_fields = ['name']
    list_per_page = 20


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'schema_name', 'plan', 'subscription_status', 'is_active', 'created_on', 'dashboard_link']
    list_filter = ['subscription_status', 'is_active', 'plan', 'country']
    search_fields = ['company_name', 'schema_name', 'email']
    readonly_fields = ['schema_name', 'created_on', 'stripe_customer_id', 'stripe_subscription_id']
    list_per_page = 25
    
    fieldsets = (
        ('معلومات الشركة', {
            'fields': ('company_name', 'company_name_ar', 'country', 'phone', 'email', 'schema_name')
        }),
        ('الخطة والاشتراك', {
            'fields': ('plan', 'subscription_status', 'trial_end')
        }),
        ('Stripe', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',)
        }),
        ('الحالة', {
            'fields': ('is_active', 'created_on')
        }),
    )
    
    def dashboard_link(self, obj):
        """Link to tenant dashboard"""
        url = reverse('admin_dashboard:tenant_dashboard', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color:#00d4ff;color:#000">📊 Dashboard</a>',
            url
        )
    dashboard_link.short_description = 'لوحة التحكم'


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary', 'domain_status']
    list_filter = ['is_primary', 'tenant']
    search_fields = ['domain', 'tenant__company_name']
    list_per_page = 30
    
    def domain_status(self, obj):
        """Show domain status with badge"""
        status = "نشط" if obj.is_primary else "فرعي"
        color = "#00d4ff" if obj.is_primary else "#38bdf8"
        return format_html(
            '<span style="background-color:{}; color:#000; padding:3px 8px; border-radius:12px; font-weight:bold; font-size:11px">{}</span>',
            color, status
        )
    domain_status.short_description = 'الحالة'


# Add dashboard link to admin index
admin.site.index_template = 'admin/index.html'
