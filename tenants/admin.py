from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Sum, Count
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
    list_display = ['name', 'tier', 'price_monthly', 'price_yearly', 'max_customers', 'max_meters', 'tenant_count', 'is_active']
    list_filter = ['tier', 'is_active']
    search_fields = ['name']
    list_per_page = 20

    def tenant_count(self, obj):
        return obj.tenant_set.count()
    tenant_count.short_description = 'عدد المستأجرين'


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'schema_name', 'plan', 'subscription_status', 'is_active', 'created_on', 'total_paid', 'dashboard_link']
    list_filter = ['subscription_status', 'is_active', 'plan', 'country']
    search_fields = ['company_name', 'schema_name', 'email']
    readonly_fields = ['schema_name', 'created_on', 'subscription_history']
    list_per_page = 25
    inlines = [TenantSubscriptionInline]
    actions = ['upgrade_to_pro', 'upgrade_to_enterprise', 'activate_tenant', 'deactivate_tenant']
    
    fieldsets = (
        ('معلومات الشركة', {
            'fields': ('company_name', 'company_name_ar', 'country', 'phone', 'email', 'schema_name')
        }),
        ('الخطة والاشتراك', {
            'fields': ('plan', 'subscription_status', 'trial_end')
        }),
        ('سجل الاشتراكات', {
            'fields': ('subscription_history',),
            'classes': ('collapse',)
        }),
        ('الحالة', {
            'fields': ('is_active', 'created_on')
        }),
    )

    def total_paid(self, obj):
        total = TenantSubscription.objects.filter(
            tenant=obj, payment_status='succeeded'
        ).aggregate(t=Sum('amount'))['t'] or 0
        return format_html('<span style="color:#34d399;font-weight:700">{}</span>', f'{total:,.2f}')
    total_paid.short_description = 'إجمالي المدفوعات'

    def subscription_history(self, obj):
        logs = TenantSubscription.objects.filter(tenant=obj)[:20]
        if not logs:
            return format_html('<span style="color:#4a7a95">لا يوجد سجل اشتراكات</span>')
        html = '<table style="width:100%;font-size:12px"><tr style="background:rgba(0,212,255,0.1)"><th>التاريخ</th><th>الإجراء</th><th>الخطة</th><th>المبلغ</th><th>الحالة</th><th>بوابة الدفع</th></tr>'
        for log in logs:
            status_color = '#34d399' if log.payment_status == 'succeeded' else ('#f43f5e' if log.payment_status == 'failed' else '#fb923c')
            plan_name = log.plan_to.name if log.plan_to else '-'
            amount = f'{log.amount:,.2f} {log.currency}' if log.amount else '-'
            gateway = log.payment_gateway or '-'
            html += f'<tr><td>{log.created_at.date()}</td><td>{log.get_action_display()}</td><td>{plan_name}</td><td>{amount}</td><td style="color:{status_color}">{log.get_payment_status_display()}</td><td>{gateway}</td></tr>'
        html += '</table>'
        return format_html(html)
    subscription_history.short_description = 'سجل الاشتراكات'

    def dashboard_link(self, obj):
        """Link to tenant change page"""
        url = reverse('admin:tenants_tenant_change', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="background-color:#00d4ff;color:#000">📊 لوحة التحكم</a>',
            url
        )
    dashboard_link.short_description = 'لوحة التحكم'

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
