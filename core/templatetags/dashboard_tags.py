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
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncMonth
    
    try:
        from billing.models import Invoice, Payment, Customer, Contract, Meter, MeterReadingSubmission, MeterReading
        
        user_count = User.objects.count()
        customer_count = Customer.objects.count()
        contract_count = Contract.objects.filter(contract_status='active').count()
        meter_count = Meter.objects.filter(meter_status='active').count()
        
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(invoice_status='paid').count()
        pending_invoices = Invoice.objects.filter(invoice_status='issued').count()
        overdue_invoices = Invoice.objects.filter(invoice_status='overdue').count()
        
        total_payments = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        total_outstanding = Invoice.objects.filter(
            invoice_status__in=['issued', 'partially_paid', 'overdue']
        ).aggregate(t=Sum('total_amount'))['t'] or 0
        
        pending_readings = MeterReadingSubmission.objects.filter(approval_status='pending')
        
        recent_invoices = list(Invoice.objects.select_related('contract__customer').order_by('-created_at')[:5])
        
        # Recent Activities for Timeline
        recent_activities = []
        # Add recent payments
        for p in Payment.objects.order_by('-payment_date')[:3]:
            recent_activities.append({
                'icon': '💳',
                'ico_bg': 'rgba(52,211,153,0.12)',
                'title': f'تم استلام دفعة: {p.amount}',
                'sub': f'رقم العملية: {p.payment_number}',
                'time': p.payment_date.strftime('%Y-%m-%d %H:%M')
            })
        # Add recent invoices
        for inv in Invoice.objects.order_by('-created_at')[:3]:
            recent_activities.append({
                'icon': '📄',
                'ico_bg': 'rgba(0,212,255,0.1)',
                'title': f'فاتورة جديدة: {inv.total_amount}',
                'sub': f'رقم الفاتورة: {inv.invoice_number}',
                'time': inv.created_at.strftime('%Y-%m-%d %H:%M')
            })
        # Sort by time
        recent_activities.sort(key=lambda x: x['time'], reverse=True)
        recent_activities = recent_activities[:5]

        # Consumption data for the last 6 months
        six_months_ago = timezone.now().date() - timedelta(days=180)
        consumption_data = MeterReading.objects.filter(
            reading_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('reading_date')
        ).values('month').annotate(
            total=Sum(models.F('current_reading') - models.F('previous_reading'))
        ).order_by('month')
        
        months_labels = []
        consumption_vals = []
        
        # Arabic month names
        ar_months = {1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو', 
                     7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'}
        
        for entry in consumption_data:
            if entry['month']:
                months_labels.append(ar_months.get(entry['month'].month, str(entry['month'].month)))
                consumption_vals.append(float(entry['total'] or 0))
        
        # Fill if empty
        if not months_labels:
            months_labels = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو']
            consumption_vals = [0, 0, 0, 0, 0, 0]

        return {
            'user_count': user_count,
            'customer_count': customer_count,
            'contract_count': contract_count,
            'meter_count': meter_count,
            'invoice_count': total_invoices,
            'paid_invoices': paid_invoices,
            'pending_invoices': pending_invoices,
            'overdue_invoices': overdue_invoices,
            'total_payments': total_payments,
            'total_outstanding': total_outstanding,
            'pending_readings': pending_readings,
            'recent_invoices': recent_invoices,
            'recent_activities_json': json.dumps(recent_activities),
            'months_labels_json': json.dumps(months_labels),
            'consumption_vals_json': json.dumps(consumption_vals),
        }
    except Exception as e:
        print(f"Error in tenant_dashboard_stats: {e}")
        return {
            'user_count': 0,
            'customer_count': 0,
            'contract_count': 0,
            'meter_count': 0,
            'invoice_count': 0,
            'paid_invoices': 0,
            'pending_invoices': 0,
            'overdue_invoices': 0,
            'total_payments': 0,
            'total_outstanding': 0,
            'pending_readings': [],
            'recent_invoices': [],
            'months_labels_json': '[]',
            'consumption_vals_json': '[]',
        }
