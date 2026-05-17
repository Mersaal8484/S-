import re
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.db.models import Sum, Count
from django.db import connection
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from .models import Tenant, Domain


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'schema_name', 'schema_status_badge', 'subscription_status', 'is_active', 'created_on', 'dashboard_link']
    list_filter = ['subscription_status', 'is_active', 'country']
    search_fields = ['company_name', 'schema_name', 'email']
    readonly_fields = ['created_on', 'schema_info']
    list_per_page = 25
    actions = ['activate_tenant', 'deactivate_tenant']
    
    fieldsets = (
        ('معلومات الشركة', {
            'fields': ('company_name', 'company_name_ar', 'country', 'phone', 'email')
        }),
        ('قاعدة البيانات', {
            'fields': ('schema_name', 'schema_info'),
            'classes': ('wide',),
            'description': 'يتم إنشاء Schema (قاعدة بيانات) منفصل ومعزول لكل مستأجر تلقائياً'
        }),
        ('حالة الاشتراك', {
            'fields': ('subscription_status', 'trial_end')
        }),
        ('⚙️ الحالة والإعدادات', {
            'fields': (('is_active', 'created_on'),)
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """Hide schema fields on add form (auto-generated)."""
        if not obj:
            return (
                ('معلومات الشركة', {
                    'fields': ('company_name', 'company_name_ar', 'country', 'phone', 'email')
                }),
                ('حالة الاشتراك', {
                    'fields': ('subscription_status', 'trial_end')
                }),
                ('الحالة', {
                    'fields': ('is_active',)
                }),
            )
        return super().get_fieldsets(request, obj)

    def save_model(self, request, obj, form, change):
        if not change:
            clean_name = re.sub(r'[^a-z0-9_]', '', obj.company_name.lower().replace(' ', '_').replace('-', '_')).strip('_')
            if not clean_name or len(clean_name) < 2:
                clean_name = re.sub(r'[^a-z0-9_]', '', obj.email.split('@')[0].lower()).strip('_')
            schema_name = clean_name[:63]
            if not schema_name or schema_name[0].isdigit():
                schema_name = 't' + schema_name if schema_name else 'company'
            base = schema_name
            counter = 1
            while Tenant.objects.filter(schema_name=schema_name).exists():
                schema_name = f"{base[:60]}_{counter}"
                counter += 1
            obj.schema_name = schema_name
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        """Show provisioning summary after successful creation."""
        msg = (
            f'تم إنشاء {obj.company_name} بنجاح. '
            f'Schema: {obj.schema_name}، '
            f'حساب المسؤول: {obj.email}'
        )
        self.message_user(request, msg)
        return super().response_add(request, obj, post_url_continue)

    def schema_info(self, obj):
        """Show schema status with details."""
        if not obj.pk:
            return mark_safe('<span style="color:#4a7a95">سيتم إنشاء schema تلقائياً عند الحفظ</span>')
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = %s)", [obj.schema_name])
            exists = cursor.fetchone()[0]
        if exists:
            admin_email = None
            with schema_context(obj.schema_name):
                admin = User.objects.filter(is_superuser=True).first()
                admin_email = admin.email if admin else 'غير موجود'
            return format_html(
                '<div style="line-height:2">'
                '<span style="color:#34d399;font-weight:700">✓ Schema موجودة ونشطة</span><br>'
                '<span style="color:#4a7a95;font-size:12px">مسؤول النظام: {}</span>'
                '</div>',
                admin_email
            )
        else:
            return mark_safe(
                '<div style="line-height:2">'
                '<span style="color:#f43f5e;font-weight:700">✗ Schema مفقودة</span><br>'
                '<span style="color:#4a7a95;font-size:12px">اضغط "حفظ" لإنشاء schema تلقائياً</span>'
                '</div>'
            )
    schema_info.short_description = 'حالة قاعدة البيانات'

    def schema_status_badge(self, obj):
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = %s)", [obj.schema_name])
            exists = cursor.fetchone()[0]
        if exists:
            return mark_safe('<span style="color:#34d399;font-weight:700">✓</span>')
        return mark_safe('<span style="color:#f43f5e;font-weight:700">✗</span>')
    schema_status_badge.short_description = 'DB'

    def dashboard_link(self, obj):
        url = reverse('admin:tenants_tenant_change', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="background:linear-gradient(135deg,#00d4ff,#38bdf8);color:#000;border:none;padding:4px 12px;font-weight:700;font-size:11px;border-radius:6px">⚙️ إدارة</a>',
            url
        )
    dashboard_link.short_description = 'الإجراءات'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'إدارة المستأجرين (شركات النظام)'
        extra_context['stats'] = {
            'total': Tenant.objects.count(),
            'active': Tenant.objects.filter(is_active=True).count(),
            'revenue': 0,
            'recent': Tenant.objects.order_by('-created_on')[:5],
        }
        return super().changelist_view(request, extra_context=extra_context)

    def activate_tenant(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'تم تنشيط {queryset.count()} مستأجر')
    activate_tenant.short_description = 'تنشيط المحدد'

    def deactivate_tenant(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'تم إيقاف {queryset.count()} مستأجر')
    deactivate_tenant.short_description = 'إيقاف المحدد'


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
