import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db import connection
from django_tenants.utils import schema_context
from django.contrib.auth.models import User

from .models import Plan, Tenant, Domain, TenantSubscription
from django.db.models import Count, Sum, Avg, Q, F
from datetime import timedelta
from decimal import Decimal


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

    # ═══ SCHEMA STATUS ═══
    with connection.cursor() as cursor:
        cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast')")
        existing_schemas = {row[0] for row in cursor.fetchall()}

    # ═══ RECENT ACTIVITY ═══
    recent_tenants = Tenant.objects.select_related('plan').order_by('-created_on')[:10]
    for t in recent_tenants:
        t.schema_status = 'موجود' if t.schema_name in existing_schemas else 'مفقود'

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
