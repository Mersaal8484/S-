import json
from django import template
from django.db import models
from django.db.models import Count, Sum

register = template.Library()


@register.simple_tag
def super_admin_stats():
    from tenants.models import Tenant, Plan, TenantSubscription
    try:
        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(is_active=True).count()
        total_plans = Plan.objects.count()
        plans = Plan.objects.filter(is_active=True)
        plan_qs = list(plans.annotate(tenant_count=Count('tenant')).values('name', 'tenant_count'))
        total = sum(p['tenant_count'] for p in plan_qs) or 1
        colors = {'Enterprise': '#a78bfa', 'Pro': '#00d4ff', 'Basic': '#38bdf8',
                  'enterprise': '#a78bfa', 'pro': '#00d4ff', 'basic': '#38bdf8'}
        fallback_colors = ['#a78bfa', '#00d4ff', '#38bdf8', '#fb923c', '#34d399', '#ec4899']
        plan_data = []
        for i, p in enumerate(plan_qs):
            plan_data.append({
                'name': p['name'],
                'count': p['tenant_count'],
                'pct': round(p['tenant_count'] / total * 100),
                'color': colors.get(p['name'], fallback_colors[i % len(fallback_colors)]),
            })
        recent_tenants = Tenant.objects.order_by('-created_on')[:5]

        # Subscription revenue stats
        total_revenue = TenantSubscription.objects.filter(
            payment_status='succeeded'
        ).aggregate(t=Sum('amount'))['t'] or 0
        recent_payments = TenantSubscription.objects.filter(
            action='payment', payment_status='succeeded'
        )[:5]
        total_payments = TenantSubscription.objects.filter(
            action='payment', payment_status='succeeded'
        ).count()
        failed_payments = TenantSubscription.objects.filter(
            action='payment', payment_status='failed'
        ).count()
        recent_upgrades = TenantSubscription.objects.filter(
            action__in=['upgraded', 'downgraded']
        )[:5]

        # Plan distribution for dashboard
        plan_distribution = []
        for p in plan_qs:
            plan_distribution.append({
                'name': p['name'],
                'count': p['tenant_count'],
            })

        return {
            'total_tenants': total_tenants,
            'active_tenants': active_tenants,
            'total_plans': total_plans,
            'plan_data_json': json.dumps(plan_data),
            'recent_tenants': recent_tenants,
            'total_revenue': total_revenue,
            'recent_payments': recent_payments,
            'total_payments': total_payments,
            'failed_payments': failed_payments,
            'recent_upgrades': recent_upgrades,
            'plan_distribution': plan_distribution,
        }
    except Exception:
        return {
            'total_tenants': 0,
            'active_tenants': 0,
            'total_plans': 0,
            'plan_data_json': '[]',
            'recent_tenants': [],
            'total_revenue': 0,
            'recent_payments': [],
            'total_payments': 0,
            'failed_payments': 0,
            'recent_upgrades': [],
            'plan_distribution': [],
        }


@register.simple_tag
def tenant_dashboard_stats():
    from django.contrib.auth.models import User
    try:
        user_count = User.objects.count()
    except Exception:
        user_count = 0
    try:
        from billing.models import Invoice, Payment
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(invoice_status='paid').count()
        pending_invoices = Invoice.objects.filter(invoice_status__in=['issued', 'overdue']).count()
        total_payments = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    except Exception:
        total_invoices = 0
        paid_invoices = 0
        pending_invoices = 0
        total_payments = 0
    recent_invoices = []
    try:
        from billing.models import Invoice
        recent_invoices = list(Invoice.objects.order_by('-created_at')[:5])
    except Exception:
        pass
    return {
        'user_count': user_count,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'pending_invoices': pending_invoices,
        'total_payments': total_payments,
        'recent_invoices': recent_invoices,
    }
