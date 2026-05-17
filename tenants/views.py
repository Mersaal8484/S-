import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db import IntegrityError, connection
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Plan, Tenant, Domain, TenantSubscription, PlatformSettings
from django.db.models import Count, Sum, Avg, Q, F
from datetime import timedelta
from decimal import Decimal
import json
from django.contrib.admin.views.decorators import staff_member_required

def landing_page(request):
    """Public landing page"""
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'public/landing.html', {'plans': plans})


def pricing(request):
    """Public pricing page"""
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'public/pricing.html', {'plans': plans})


def register(request):
    """Tenant registration - step 1: choose plan and fill company info"""
    if request.method == 'POST':
        with schema_context('public'):
            plan_id = request.POST.get('plan')
            plan = get_object_or_404(Plan, pk=plan_id)

            company_name = request.POST.get('company_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            password = request.POST.get('password')

            if not company_name or not email or not password:
                messages.error(request, 'يرجى تعبئة جميع الحقول المطلوبة')
                return redirect('tenants:register')

            # Improve schema name generation: handle Arabic by using email prefix if name is non-ASCII
            clean_name = re.sub(r'[^a-z0-9_]', '', company_name.lower().replace(' ', '_').replace('-', '_')).strip('_')
            if not clean_name or len(clean_name) < 2:
                # Use email prefix if company name is all Arabic/special chars
                clean_name = re.sub(r'[^a-z0-9_]', '', email.split('@')[0].lower()).strip('_')

            schema_name = clean_name[:63]
            if not schema_name or schema_name[0].isdigit():
                schema_name = 't' + schema_name if schema_name else 'company'

            # Ensure uniqueness
            base_schema = schema_name
            counter = 1
            while Tenant.objects.filter(schema_name=schema_name).exists():
                schema_name = f"{base_schema[:60]}_{counter}"
                counter += 1

            tenant = Tenant.objects.create(
                schema_name=schema_name,
                company_name=company_name,
                email=email,
                phone=phone,
                plan=plan,
                is_active=True,
            )

            Domain.objects.create(
                domain=f"{schema_name}.{settings.ALLOWED_HOSTS[0] if isinstance(settings.ALLOWED_HOSTS, list) else settings.ALLOWED_HOSTS.split(',')[0] if hasattr(settings.ALLOWED_HOSTS, 'split') else 'yoursaas.com'}",
                tenant=tenant,
                is_primary=True,
            )

            with schema_context(tenant.schema_name):
                try:
                    User.objects.create_superuser(
                        username=email,
                        email=email,
                        password=password,
                    )
                except IntegrityError:
                    user = User.objects.get(username=email)
                    user.set_password(password)
                    user.is_superuser = True
                    user.is_staff = True
                    user.save()

            request.session['tenant_id'] = tenant.id
            messages.success(request, f'تم إنشاء الحساب بنجاح! مرحباً {company_name}')
            return redirect('tenants:register_success', tenant_id=tenant.id)

    plans = Plan.objects.filter(is_active=True)
    return render(request, 'public/register.html', {'plans': plans})


def register_success(request, tenant_id):
    """Registration success page with subdomain info"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    domain = tenant.domains.filter(is_primary=True).first()
    return render(request, 'public/register_success.html', {
        'tenant': tenant,
        'domain': domain,
    })


def upgrade_checkout(request, tenant_id):
    """Direct plan upgrade (no payment gateway for now)"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    plan_id = request.GET.get('plan')
    plan = get_object_or_404(Plan, pk=plan_id)

    if plan.tier == tenant.plan.tier:
        messages.info(request, 'أنت بالفعل مشترك في هذه الخطة')
        return redirect('tenants:register_success', tenant_id=tenant.id)

    billing_cycle = request.GET.get('cycle', 'monthly')
    amount = plan.price_monthly if billing_cycle == 'monthly' else plan.price_yearly

    # Direct upgrade - في المستقبل سيتم التكامل مع بوابة دفع محلية
    old_plan = tenant.plan
    tenant.plan = plan
    tenant.subscription_status = 'active'
    tenant.save()

    from .models import TenantSubscription
    TenantSubscription.objects.create(
        tenant=tenant,
        action='upgraded',
        plan_from=old_plan,
        plan_to=plan,
        amount=amount,
        currency='SAR',
        payment_status='succeeded',
        notes=f'ترقية مباشرة - {billing_cycle}'
    )

    messages.success(request, f'تم ترقية حسابك إلى {plan.name} بنجاح!')
    return redirect('tenants:register_success', tenant_id=tenant.id)


def upgrade_success(request, tenant_id):
    """Upgrade completed successfully"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    messages.success(request, 'تمت الترقية بنجاح ✅')
    return redirect('tenants:register_success', tenant_id=tenant.id)


@staff_member_required
def tenant_dashboard(request):
    active_page = 'settings' if request.path.startswith('/admin/settings/') else request.GET.get('page', 'overview')

    from billing.models import SystemSettings, SubscriptionType, InvoiceLineTemplate

    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()

    subscription_types = list(SubscriptionType.objects.all())
    templates_by_type = {}
    for st in subscription_types:
        templates = InvoiceLineTemplate.objects.filter(type=st)
        templates_by_type[st.id] = {
            'type': {
                'id': st.id,
                'name_ar': st.name_ar,
                'name_en': st.name_en,
                'is_active': st.is_active,
                'description': st.description,
                'code': getattr(st, 'code', None),
            },
            'templates': list(templates.values(
                'id', 'line_order', 'line_name_ar', 'line_name_en',
                'calculation_type', 'is_taxable'
            ))
        }

    context = {
        'active_page': active_page,
        'settings': settings_obj,
        'subscription_types': subscription_types,
        'templates_by_type_json': json.dumps(templates_by_type),
    }

    return render(request, 'admin/index_tenant.html', context)


@staff_member_required
def platform_settings(request):
    """Super Admin: Platform-wide settings management"""
    ps = PlatformSettings.get_settings()

    if request.method == 'POST':
        section = request.POST.get('section', 'platform')

        if section == 'platform':
            ps.platform_name = request.POST.get('platform_name', ps.platform_name)
            ps.platform_name_ar = request.POST.get('platform_name_ar', ps.platform_name_ar)
            ps.support_email = request.POST.get('support_email', ps.support_email)
            ps.support_phone = request.POST.get('support_phone', ps.support_phone)
            ps.platform_url = request.POST.get('platform_url', ps.platform_url)

        elif section == 'stripe':
            ps.stripe_mode = request.POST.get('stripe_mode', ps.stripe_mode)
            # Only update keys if provided (not blank)
            if request.POST.get('stripe_publishable_key'):
                ps.stripe_publishable_key = request.POST.get('stripe_publishable_key')
            if request.POST.get('stripe_secret_key'):
                ps.stripe_secret_key = request.POST.get('stripe_secret_key')
            if request.POST.get('stripe_webhook_secret'):
                ps.stripe_webhook_secret = request.POST.get('stripe_webhook_secret')

        elif section == 'webhook':
            if request.POST.get('webhook_secret_global'):
                ps.webhook_secret_global = request.POST.get('webhook_secret_global')
            ps.webhook_url_payment = request.POST.get('webhook_url_payment', ps.webhook_url_payment)
            ps.webhook_url_subscription = request.POST.get('webhook_url_subscription', ps.webhook_url_subscription)
            ps.webhook_retry_attempts = int(request.POST.get('webhook_retry_attempts', ps.webhook_retry_attempts))
            ps.webhook_timeout_seconds = int(request.POST.get('webhook_timeout_seconds', ps.webhook_timeout_seconds))

        elif section == 'api':
            ps.api_rate_limit_per_minute = int(request.POST.get('api_rate_limit_per_minute', ps.api_rate_limit_per_minute))
            ps.api_max_page_size = int(request.POST.get('api_max_page_size', ps.api_max_page_size))
            ps.api_jwt_expiry_minutes = int(request.POST.get('api_jwt_expiry_minutes', ps.api_jwt_expiry_minutes))
            ps.api_allow_cors = request.POST.get('api_allow_cors') == 'on'
            ps.api_cors_origins = request.POST.get('api_cors_origins', ps.api_cors_origins)
            ps.api_documentation_enabled = request.POST.get('api_documentation_enabled') == 'on'

        elif section == 'accounting':
            ps.default_currency = request.POST.get('default_currency', ps.default_currency)
            ps.default_vat_rate = Decimal(request.POST.get('default_vat_rate', str(ps.default_vat_rate)))
            ps.fiscal_year_start_month = int(request.POST.get('fiscal_year_start_month', ps.fiscal_year_start_month))
            ps.enable_double_entry = request.POST.get('enable_double_entry') == 'on'
            ps.auto_create_journal_entries = request.POST.get('auto_create_journal_entries') == 'on'
            ps.invoice_prefix = request.POST.get('invoice_prefix', ps.invoice_prefix)
            ps.invoice_auto_number = request.POST.get('invoice_auto_number') == 'on'
            ps.invoice_due_days = int(request.POST.get('invoice_due_days', ps.invoice_due_days))

        elif section == 'payments':
            ps.payment_grace_days = int(request.POST.get('payment_grace_days', ps.payment_grace_days))
            ps.late_payment_penalty_pct = Decimal(request.POST.get('late_payment_penalty_pct', str(ps.late_payment_penalty_pct)))
            ps.allow_installments = request.POST.get('allow_installments') == 'on'
            ps.max_installment_months = int(request.POST.get('max_installment_months', ps.max_installment_months))
            ps.installment_min_amount = Decimal(request.POST.get('installment_min_amount', str(ps.installment_min_amount)))
            ps.allow_partial_payment = request.POST.get('allow_partial_payment') == 'on'
            ps.allow_advance_payment = request.POST.get('allow_advance_payment') == 'on'

        elif section == 'ewallet':
            ps.ewallet_enabled = request.POST.get('ewallet_enabled') == 'on'
            ps.stcpay_enabled = request.POST.get('stcpay_enabled') == 'on'
            if request.POST.get('stcpay_merchant_id'):
                ps.stcpay_merchant_id = request.POST.get('stcpay_merchant_id')
            if request.POST.get('stcpay_api_key'):
                ps.stcpay_api_key = request.POST.get('stcpay_api_key')
            if request.POST.get('stcpay_webhook_secret'):
                ps.stcpay_webhook_secret = request.POST.get('stcpay_webhook_secret')
            ps.mada_enabled = request.POST.get('mada_enabled') == 'on'
            if request.POST.get('mada_merchant_id'):
                ps.mada_merchant_id = request.POST.get('mada_merchant_id')
            if request.POST.get('mada_api_key'):
                ps.mada_api_key = request.POST.get('mada_api_key')
            ps.tabby_enabled = request.POST.get('tabby_enabled') == 'on'
            if request.POST.get('tabby_api_key'):
                ps.tabby_api_key = request.POST.get('tabby_api_key')
            if request.POST.get('tabby_secret_key'):
                ps.tabby_secret_key = request.POST.get('tabby_secret_key')
            ps.tamara_enabled = request.POST.get('tamara_enabled') == 'on'
            if request.POST.get('tamara_api_key'):
                ps.tamara_api_key = request.POST.get('tamara_api_key')
            if request.POST.get('tamara_webhook_secret'):
                ps.tamara_webhook_secret = request.POST.get('tamara_webhook_secret')

        elif section == 'tenants_cfg':
            ps.default_trial_days = int(request.POST.get('default_trial_days', ps.default_trial_days))
            ps.auto_activate_on_payment = request.POST.get('auto_activate_on_payment') == 'on'
            ps.require_domain_verification = request.POST.get('require_domain_verification') == 'on'
            ps.allowed_custom_domains = request.POST.get('allowed_custom_domains') == 'on'
            ps.max_domains_per_tenant = int(request.POST.get('max_domains_per_tenant', ps.max_domains_per_tenant))
            ps.auto_send_welcome_email = request.POST.get('auto_send_welcome_email') == 'on'

        elif section == 'notifications':
            ps.sms_provider = request.POST.get('sms_provider', ps.sms_provider)
            if request.POST.get('sms_api_key'):
                ps.sms_api_key = request.POST.get('sms_api_key')
            ps.sms_sender_id = request.POST.get('sms_sender_id', ps.sms_sender_id)
            ps.email_host = request.POST.get('email_host', ps.email_host)
            ps.email_port = int(request.POST.get('email_port', ps.email_port))
            ps.email_use_tls = request.POST.get('email_use_tls') == 'on'
            ps.email_host_user = request.POST.get('email_host_user', ps.email_host_user)
            if request.POST.get('email_host_password'):
                ps.email_host_password = request.POST.get('email_host_password')
            ps.default_from_email = request.POST.get('default_from_email', ps.default_from_email)

        ps.updated_by = request.user.username
        ps.save()
        messages.success(request, f'✅ تم حفظ إعدادات "{section}" بنجاح')
        return redirect(f"{request.path}?section={section}")

    # Stats for sidebar
    active_section = request.GET.get('section', 'platform')
    plans = Plan.objects.all().order_by('tier')
    tenants_count = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()

    return render(request, 'admin/super_admin_dashboard.html', {
        'ps': ps,
        'active_section': active_section,
        'active_tab': 'settings',
        'plans': plans,
        'tenants_count': tenants_count,
        'active_tenants': active_tenants,
    })


@staff_member_required
def plan_management(request):
    """Super Admin: Manage SaaS plans"""
    plans = Plan.objects.all().order_by('tier')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            Plan.objects.create(
                name=request.POST.get('name'),
                tier=request.POST.get('tier', 'basic'),
                price_monthly=Decimal(request.POST.get('price_monthly', '0')),
                price_yearly=Decimal(request.POST.get('price_yearly', '0')),
                max_customers=int(request.POST.get('max_customers', 1000)),
                max_meters=int(request.POST.get('max_meters', 5000)),
                max_users=int(request.POST.get('max_users', 10)),
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'تم إنشاء الخطة بنجاح ✅')
        elif action == 'toggle':
            plan = get_object_or_404(Plan, pk=request.POST.get('plan_id'))
            plan.is_active = not plan.is_active
            plan.save()
            messages.success(request, f'تم تحديث حالة الخطة {plan.name}')
        elif action == 'upgrade_tenant':
            tenant = get_object_or_404(Tenant, pk=request.POST.get('tenant_id'))
            plan = get_object_or_404(Plan, pk=request.POST.get('plan_id'))
            old_plan = tenant.plan
            tenant.plan = plan
            tenant.subscription_status = 'active'
            tenant.save()
            TenantSubscription.objects.create(
                tenant=tenant, action='upgraded',
                plan_from=old_plan, plan_to=plan,
                notes='ترقية يدوية من لوحة الإعدادات'
            )
            messages.success(request, f'تمت ترقية {tenant.company_name} إلى {plan.name}')
        return redirect('tenants:plan_management')

    tenants = Tenant.objects.select_related('plan').all().order_by('-created_on')
    return render(request, 'admin/plan_management.html', {
        'plans': plans, 'tenants': tenants,
    })


def super_admin_dashboard(request):
    """Super Admin Dashboard with Advanced Live Statistics"""
    if not request.user.is_staff:
        messages.error(request, 'غير مصرح لك بالوصول')
        return redirect('/')

    # ═══ TENANT STATISTICS ═══
    total_tenants = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()
    inactive_tenants = total_tenants - active_tenants

    # New tenants last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_tenants_30d = Tenant.objects.filter(created_at__gte=thirty_days_ago).count()

    # ═══ PLAN DISTRIBUTION ═══
    plan_stats = Tenant.objects.values('plan__name').annotate(
        count=Count('id'),
        revenue=Sum(F('plan__price_monthly'))
    ).order_by('-count')

    # ═══ REVENUE CALCULATIONS ═══
    # MRR - Monthly Recurring Revenue
    mrr = Tenant.objects.filter(is_active=True).aggregate(
        total=Sum('plan__price_monthly')
    )['total'] or Decimal('0')

    # ARR - Annual Recurring Revenue
    arr = mrr * 12

    # Total revenue from subscriptions
    total_revenue = TenantSubscription.objects.filter(
        payment_status='succeeded'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # ═══ SUBSCRIPTION STATUS ═══
    subscription_status = Tenant.objects.values('subscription_status').annotate(
        count=Count('id')
    )

    # ═══ GROWTH METRICS ═══
    # Last 12 months growth
    monthly_growth = []
    for i in range(11, -1, -1):
        start = timezone.now() - timedelta(days=30*i)
        end = start + timedelta(days=30)
        count = Tenant.objects.filter(created_at__gte=start, created_at__lt=end).count()
        monthly_growth.append({
            'month': start.strftime('%b'),
            'count': count
        })

    # ═══ RECENT ACTIVITY ═══
    recent_tenants = Tenant.objects.select_related('plan').order_by('-created_at')[:10]
    recent_subscriptions = TenantSubscription.objects.select_related(
        'tenant', 'plan_from', 'plan_to'
    ).order_by('-created_at')[:10]

    # ═══ TOP PERFORMERS ═══
    top_tenants_by_plan = Tenant.objects.filter(is_active=True).select_related('plan').order_by(
        '-plan__tier', '-created_at'
    )[:5]

    # ═══ HEALTH METRICS ═══
    # Churn Rate (last 30 days)
    churned_tenants = Tenant.objects.filter(
        is_active=False,
        updated_at__gte=thirty_days_ago
    ).count()
    churn_rate = (churned_tenants / total_tenants * 100) if total_tenants > 0 else 0

    # Average tenant lifetime (days)
    avg_lifetime = Tenant.objects.filter(is_active=True).annotate(
        lifetime=timezone.now() - F('created_at')
    ).aggregate(avg=Avg('lifetime'))['avg']
    avg_lifetime_days = avg_lifetime.days if avg_lifetime else 0

    context = {
        # Counts
        'total_tenants': total_tenants,
        'active_tenants': active_tenants,
        'inactive_tenants': inactive_tenants,
        'new_tenants_30d': new_tenants_30d,

        # Revenue
        'mrr': mrr,
        'arr': arr,
        'total_revenue': total_revenue,

        # Plans
        'plan_stats': plan_stats,
        'subscription_status': subscription_status,

        # Growth
        'monthly_growth': monthly_growth,

        # Recent
        'recent_tenants': recent_tenants,
        'recent_subscriptions': recent_subscriptions,
        'top_tenants': top_tenants_by_plan,

        # Health
        'churn_rate': round(churn_rate, 2),
        'avg_lifetime_days': avg_lifetime_days,
    }

    return render(request, 'admin/super_admin_dashboard.html', context)
