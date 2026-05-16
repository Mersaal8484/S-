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
    list_display = ['company_info', 'schema_name_badge', 'plan_badge', 'status_badge', 'active_toggle', 'total_paid', 'created_on', 'dashboard_link']
    list_filter = ['subscription_status', 'is_active', 'plan', 'country']
    search_fields = ['company_name', 'company_name_ar', 'schema_name', 'email']
    readonly_fields = ['schema_name', 'created_on', 'subscription_history']
    list_per_page = 25
    inlines = [TenantSubscriptionInline]
    actions = ['upgrade_to_pro', 'upgrade_to_enterprise', 'activate_tenant', 'deactivate_tenant']
    
    fieldsets = (
        ('🏢 معلومات الشركة', {
            'fields': (('company_name', 'company_name_ar'), ('country', 'phone', 'email'), 'schema_name')
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

    def company_info(self, obj):
        name = obj.company_name_ar or obj.company_name
        return format_html(
            '<div style="line-height:1.2"><strong>{}</strong><br><small style="color:#64748b">{}</small></div>',
            name, obj.email
        )
    company_info.short_description = 'الشركة'

    def schema_name_badge(self, obj):
        return format_html(
            '<code style="background:rgba(0,212,255,0.1);color:#00d4ff;padding:2px 6px;border-radius:4px;font-size:11px">{}</code>',
            obj.schema_name
        )
    schema_name_badge.short_description = 'المعرف (Schema)'

    def plan_badge(self, obj):
        if not obj.plan: return "-"
        colors = {'basic': '#94a3b8', 'pro': '#00d4ff', 'enterprise': '#a78bfa'}
        color = colors.get(obj.plan.tier, '#94a3b8')
        return format_html(
            '<span style="border:1px solid {};color:{};padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600">{}</span>',
            color, color, obj.plan.name
        )
    plan_badge.short_description = 'الخطة'

    def status_badge(self, obj):
        colors = {
            'active': '#10b981',
            'trialing': '#3b82f6',
            'past_due': '#f59e0b',
            'canceled': '#ef4444',
        }
        color = colors.get(obj.subscription_status, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700">{}</span>',
            color, obj.get_subscription_status_display()
        )
    status_badge.short_description = 'حالة الاشتراك'

    def active_toggle(self, obj):
        icon = 'check-circle' if obj.is_active else 'times-circle'
        color = '#10b981' if obj.is_active else '#f43f5e'
        return format_html('<i class="fas fa-{}" style="color:{};font-size:16px"></i>', icon, color)
    active_toggle.short_description = 'نشط'

    def total_paid(self, obj):
        total = TenantSubscription.objects.filter(
            tenant=obj, payment_status='succeeded'
        ).aggregate(t=Sum('amount'))['t'] or 0
        return format_html('<span style="color:#34d399;font-weight:700">{}</span>', f'{total:,.2f} SAR')
    total_paid.short_description = 'إجمالي الدفع'

    def subscription_history(self, obj):
        logs = TenantSubscription.objects.filter(tenant=obj)[:15]
        if not logs:
            return format_html('<span style="color:#64748b">لا يوجد سجل اشتراكات</span>')
        
        html = '<div class="result-list-wrap"><table style="width:100%;font-size:12px;border-collapse:collapse">'
        html += '<tr style="background:rgba(0,212,255,0.05)">'
        html += '<th style="padding:8px">التاريخ</th><th style="padding:8px">الإجراء</th><th style="padding:8px">الخطة</th><th style="padding:8px">المبلغ</th><th style="padding:8px">الحالة</th></tr>'
        
        for log in logs:
            status_color = '#34d399' if log.payment_status == 'succeeded' else ('#f43f5e' if log.payment_status == 'failed' else '#fb923c')
            plan_name = log.plan_to.name if log.plan_to else '-'
            amount = f'{log.amount:,.2f} {log.currency}' if log.amount else '-'
            html += f'<tr style="border-bottom:1px solid rgba(0,212,255,0.05)">'
            html += f'<td style="padding:8px">{log.created_at.date()}</td>'
            html += f'<td style="padding:8px">{log.get_action_display()}</td>'
            html += f'<td style="padding:8px">{plan_name}</td>'
            html += f'<td style="padding:8px">{amount}</td>'
            html += f'<td style="padding:8px;color:{status_color};font-weight:600">{log.get_payment_status_display()}</td>'
            html += '</tr>'
        html += '</table></div>'
        return format_html(html)
    subscription_history.short_description = 'سجل العمليات'

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
