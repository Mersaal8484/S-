import re
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.db.models import Sum, Count
from django.db import connection
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from .models import Plan, Tenant, Domain, TenantSubscription


class TenantSubscriptionInline(admin.TabularInline):
    model = TenantSubscription
    extra = 0
    readonly_fields = ['action', 'plan_from', 'plan_to', 'amount', 'currency', 'payment_status', 'transaction_id', 'payment_gateway', 'created_at']
    can_delete = False
    max_num = 0
    ordering = ['-created_at']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name_badge', 'tier_badge', 'price_monthly', 'price_yearly', 'max_customers', 'tenant_count', 'is_active']
    list_filter = ['tier', 'is_active']
    search_fields = ['name']
    list_per_page = 20

    def name_badge(self, obj):
        return format_html('<span style="font-weight:700;color:#00d4ff">{}</span>', obj.name)
    name_badge.short_description = 'اسم الخطة'

    def tier_badge(self, obj):
        colors = {'basic': '#94a3b8', 'pro': '#00d4ff', 'enterprise': '#a78bfa'}
        color = colors.get(obj.tier, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#000;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase">{}</span>',
            color, obj.get_tier_display()
        )
    tier_badge.short_description = 'المستوى'

    def tenant_count(self, obj):
        return obj.tenant_set.count()
    tenant_count.short_description = 'عدد المستأجرين'


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'schema_name', 'schema_status_badge', 'plan', 'subscription_status', 'is_active', 'created_on', 'total_paid', 'dashboard_link']
    list_filter = ['subscription_status', 'is_active', 'plan', 'country']
    search_fields = ['company_name', 'schema_name', 'email']
    readonly_fields = ['created_on', 'subscription_history', 'schema_info']
    list_per_page = 25
    inlines = [TenantSubscriptionInline]
    actions = ['upgrade_to_pro', 'upgrade_to_enterprise', 'activate_tenant', 'deactivate_tenant']
    
    fieldsets = (
        ('معلومات الشركة', {
            'fields': ('company_name', 'company_name_ar', 'country', 'phone', 'email')
        }),
        ('قاعدة البيانات', {
            'fields': ('schema_name', 'schema_info'),
            'classes': ('wide',),
            'description': 'يتم إنشاء Schema (قاعدة بيانات) منفصل ومعزول لكل مستأجر تلقائياً'
        }),
        ('💳 الخطة والاشتراك', {
            'fields': (('plan', 'subscription_status'), 'trial_end')
        }),
        ('📜 سجل العمليات', {
            'fields': ('subscription_history',),
            'classes': ('collapse',)
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
                ('الخطة والاشتراك', {
                    'fields': ('plan', 'subscription_status', 'trial_end')
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

    def total_paid(self, obj):
        total = TenantSubscription.objects.filter(
            tenant=obj, payment_status='succeeded'
        ).aggregate(t=Sum('amount'))['t'] or 0
        return format_html('<span style="color:#34d399;font-weight:700">{}</span>', f'{total:,.2f} SAR')
    total_paid.short_description = 'إجمالي الدفع'

    def subscription_history(self, obj):
        logs = TenantSubscription.objects.filter(tenant=obj)[:15]
        if not logs:
            return mark_safe('<span style="color:#4a7a95">لا يوجد سجل اشتراكات</span>')
        html = '<table style="width:100%;font-size:12px"><tr style="background:rgba(0,212,255,0.1)"><th>التاريخ</th><th>الإجراء</th><th>الخطة</th><th>المبلغ</th><th>الحالة</th><th>بوابة الدفع</th></tr>'
        for log in logs:
            status_color = '#34d399' if log.payment_status == 'succeeded' else ('#f43f5e' if log.payment_status == 'failed' else '#fb923c')
            plan_name = log.plan_to.name if log.plan_to else '-'
            amount = f'{log.amount:,.2f} {log.currency}' if log.amount else '-'
            gateway = log.payment_gateway or '-'
            html += f'<tr><td>{log.created_at.date()}</td><td>{log.get_action_display()}</td><td>{plan_name}</td><td>{amount}</td><td style="color:{status_color}">{log.get_payment_status_display()}</td><td>{gateway}</td></tr>'
        html += '</table>'
        return mark_safe(html)
    subscription_history.short_description = 'سجل الاشتراكات'

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
            'revenue': TenantSubscription.objects.filter(payment_status='succeeded').aggregate(Sum('amount'))['amount__sum'] or 0,
            'recent': Tenant.objects.order_by('-created_on')[:5],
        }
        return super().changelist_view(request, extra_context=extra_context)

    def upgrade_to_pro(self, request, queryset):
        pro = Plan.objects.filter(tier='pro').first()
        if not pro:
            self.message_user(request, 'يجب إنشاء خطة Pro أولاً', level='ERROR')
            return
        for tenant in queryset:
            old_plan = tenant.plan
            tenant.plan = pro
            tenant.save()
            TenantSubscription.objects.create(
                tenant=tenant, action='upgraded',
                plan_from=old_plan, plan_to=pro,
                notes='ترقية يدوية من لوحة الإدارة'
            )
        self.message_user(request, f'تم ترقية {queryset.count()} مستأجر إلى Pro')
    upgrade_to_pro.short_description = 'ترقية المحدد إلى Pro'

    def upgrade_to_enterprise(self, request, queryset):
        enterprise = Plan.objects.filter(tier='enterprise').first()
        if not enterprise:
            self.message_user(request, 'يجب إنشاء خطة Enterprise أولاً', level='ERROR')
            return
        for tenant in queryset:
            old_plan = tenant.plan
            tenant.plan = enterprise
            tenant.save()
            TenantSubscription.objects.create(
                tenant=tenant, action='upgraded',
                plan_from=old_plan, plan_to=enterprise,
                notes='ترقية يدوية من لوحة الإدارة'
            )
        self.message_user(request, f'تم ترقية {queryset.count()} مستأجر إلى Enterprise')
    upgrade_to_enterprise.short_description = 'ترقية المحدد إلى Enterprise'

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


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'get_action_display', 'plan_to', 'amount', 'currency', 'payment_status', 'payment_gateway', 'created_at']
    list_filter = ['action', 'payment_status', 'payment_gateway', 'created_at']
    search_fields = ['tenant__company_name', 'transaction_id']
    date_hierarchy = 'created_at'
    list_per_page = 30
    readonly_fields = ['tenant', 'action', 'plan_from', 'plan_to', 'amount', 'currency', 'payment_status', 'transaction_id', 'payment_gateway', 'created_at']


# Add dashboard link to admin index
admin.site.index_template = 'admin/index.html'
