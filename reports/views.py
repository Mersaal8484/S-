from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import ReportDefinition, ReportExecution


@login_required
def reports_dashboard(request):
    """لوحة التقارير الرئيسية"""
    recent_reports = ReportExecution.objects.select_related('report', 'executed_by').order_by('-created_at')[:10]
    
    report_types = ReportDefinition.REPORT_TYPES
    
    context = {
        'recent_reports': recent_reports,
        'report_types': report_types,
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
def kpi_dashboard(request):
    """مؤشرات الأداء الرئيسية (KPIs)"""
    from billing.models import Invoice, Payment, Contract, Customer
    from notifications.models import SMSLog
    
    # Date filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default: last 30 days
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # === FINANCIAL KPIs ===
    invoices = Invoice.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date)
    total_invoices = invoices.count()
    total_revenue = invoices.aggregate(total=Sum('total'))['total'] or Decimal('0')
    paid_invoices = invoices.filter(payment_status='paid').count()
    payment_rate = (paid_invoices / total_invoices * 100) if total_invoices > 0 else 0
    
    # === CUSTOMER KPIs ===
    total_customers = Customer.objects.filter(is_active=True).count()
    new_customers = Customer.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
    
    # === CONTRACT KPIs ===
    active_contracts = Contract.objects.filter(status='active').count()
    expiring_soon = Contract.objects.filter(
        end_date__lte=timezone.now().date() + timedelta(days=30),
        status='active'
    ).count()
    
    # === COLLECTION KPIs ===
    payments = Payment.objects.filter(payment_date__gte=start_date, payment_date__lte=end_date)
    total_collected = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    collection_rate = (total_collected / total_revenue * 100) if total_revenue > 0 else 0
    
    # === NOTIFICATION KPIs ===
    sms_sent = SMSLog.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
    sms_success = SMSLog.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date,
        status='sent'
    ).count()
    sms_success_rate = (sms_success / sms_sent * 100) if sms_sent > 0 else 0
    
    # === TREND DATA (Last 7 days) ===
    daily_revenue = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        day_revenue = Invoice.objects.filter(issue_date=day).aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        daily_revenue.append({
            'date': day.strftime('%m/%d'),
            'revenue': float(day_revenue)
        })
    
    context = {
        # Filters
        'start_date': start_date,
        'end_date': end_date,
        
        # Financial
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,
        'paid_invoices': paid_invoices,
        'payment_rate': round(payment_rate, 2),
        
        # Customers
        'total_customers': total_customers,
        'new_customers': new_customers,
        
        # Contracts
        'active_contracts': active_contracts,
        'expiring_soon': expiring_soon,
        
        # Collections
        'total_collected': total_collected,
        'collection_rate': round(collection_rate, 2),
        
        # Notifications
        'sms_sent': sms_sent,
        'sms_success': sms_success,
        'sms_success_rate': round(sms_success_rate, 2),
        
        # Trends
        'daily_revenue': daily_revenue,
    }
    
    return render(request, 'reports/kpi_dashboard.html', context)


@login_required
def consumption_report(request):
    """تقرير الاستهلاك (كهرباء، مياه، خدمات)"""
    from billing.models import MeterReading, Contract
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    service_type = request.GET.get('service_type', '')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get readings
    readings = MeterReading.objects.filter(
        reading_date__gte=start_date,
        reading_date__lte=end_date
    ).select_related('contract', 'contract__customer', 'contract__service_type')
    
    if service_type:
        readings = readings.filter(contract__service_type__name__icontains=service_type)
    
    # Aggregations
    total_consumption = readings.aggregate(total=Sum('consumption'))['total'] or Decimal('0')
    avg_consumption = readings.aggregate(avg=Avg('consumption'))['avg'] or Decimal('0')
    
    # Top consumers
    top_consumers = readings.values(
        'contract__customer__name',
        'contract__service_type__name'
    ).annotate(
        total_consumption=Sum('consumption'),
        reading_count=Count('id')
    ).order_by('-total_consumption')[:10]
    
    # By service type
    by_service = readings.values('contract__service_type__name').annotate(
        total=Sum('consumption'),
        count=Count('id')
    ).order_by('-total')
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'service_type': service_type,
        'readings': readings[:100],  # Limit for performance
        'total_consumption': total_consumption,
        'avg_consumption': avg_consumption,
        'top_consumers': top_consumers,
        'by_service': by_service,
    }
    
    return render(request, 'reports/consumption_report.html', context)



@login_required
def collection_report(request):
    """تقرير أداء المحصّلين"""
    from billing.models import Payment, Collector
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    collector_id = request.GET.get('collector')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get payments
    payments = Payment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    ).select_related('collector', 'invoice', 'invoice__customer')
    
    if collector_id:
        payments = payments.filter(collector_id=collector_id)
    
    # Aggregations
    total_collected = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    payment_count = payments.count()
    
    # By collector
    by_collector = payments.values(
        'collector__name'
    ).annotate(
        total_amount=Sum('amount'),
        payment_count=Count('id'),
        avg_amount=Avg('amount')
    ).order_by('-total_amount')
    
    # By payment method
    by_method = payments.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Daily collections (last 14 days)
    daily_collections = []
    for i in range(13, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        day_total = Payment.objects.filter(payment_date=day).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        daily_collections.append({
            'date': day.strftime('%m/%d'),
            'amount': float(day_total)
        })
    
    # All collectors for filter
    collectors = Collector.objects.filter(is_active=True)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'collector_id': collector_id,
        'payments': payments[:50],
        'total_collected': total_collected,
        'payment_count': payment_count,
        'by_collector': by_collector,
        'by_method': by_method,
        'daily_collections': daily_collections,
        'collectors': collectors,
    }
    
    return render(request, 'reports/collection_report.html', context)


@login_required
def notifications_report(request):
    """تقرير الإشعارات (SMS, WhatsApp, Email)"""
    from notifications.models import SMSLog, Notification
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    channel = request.GET.get('channel', '')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=7)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # SMS Logs
    sms_logs = SMSLog.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).select_related('provider')
    
    total_sms = sms_logs.count()
    sms_sent = sms_logs.filter(status='sent').count()
    sms_failed = sms_logs.filter(status='failed').count()
    sms_success_rate = (sms_sent / total_sms * 100) if total_sms > 0 else 0
    
    # Notifications
    notifications = Notification.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    if channel:
        notifications = notifications.filter(channel=channel)
    
    total_notifications = notifications.count()
    notifications_sent = notifications.filter(status='sent').count()
    notifications_failed = notifications.filter(status='failed').count()
    
    # By channel
    by_channel = notifications.values('channel').annotate(
        total=Count('id'),
        sent=Count('id', filter=Q(status='sent')),
        failed=Count('id', filter=Q(status='failed'))
    )
    
    # By provider
    by_provider = sms_logs.values('provider__name').annotate(
        total=Count('id'),
        sent=Count('id', filter=Q(status='sent')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('-total')
    
    # Daily trend (last 7 days)
    daily_sms = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        day_count = SMSLog.objects.filter(
            created_at__date=day
        ).count()
        daily_sms.append({
            'date': day.strftime('%m/%d'),
            'count': day_count
        })
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'channel': channel,
        
        # SMS Stats
        'total_sms': total_sms,
        'sms_sent': sms_sent,
        'sms_failed': sms_failed,
        'sms_success_rate': round(sms_success_rate, 2),
        
        # Notification Stats
        'total_notifications': total_notifications,
        'notifications_sent': notifications_sent,
        'notifications_failed': notifications_failed,
        
        # Breakdowns
        'by_channel': by_channel,
        'by_provider': by_provider,
        'daily_sms': daily_sms,
        
        # Recent logs
        'recent_sms': sms_logs.order_by('-created_at')[:50],
    }
    
    return render(request, 'reports/notifications_report.html', context)


@login_required
def invoicing_report(request):
    """تقرير الفواتير والدفعات"""
    from billing.models import Invoice, Payment
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status', '')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get invoices
    invoices = Invoice.objects.filter(
        issue_date__gte=start_date,
        issue_date__lte=end_date
    ).select_related('customer', 'contract')
    
    if status:
        invoices = invoices.filter(payment_status=status)
    
    # Aggregations
    total_invoices = invoices.count()
    total_amount = invoices.aggregate(total=Sum('total'))['total'] or Decimal('0')
    paid_amount = invoices.filter(payment_status='paid').aggregate(
        total=Sum('total')
    )['total'] or Decimal('0')
    outstanding = total_amount - paid_amount
    
    # By status
    by_status = invoices.values('payment_status').annotate(
        count=Count('id'),
        total=Sum('total')
    )
    
    # Overdue invoices
    overdue = invoices.filter(
        due_date__lt=timezone.now().date(),
        payment_status__in=['pending', 'partial']
    )
    overdue_count = overdue.count()
    overdue_amount = overdue.aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # Top customers by invoice amount
    top_customers = invoices.values(
        'customer__name'
    ).annotate(
        total_invoices=Count('id'),
        total_amount=Sum('total')
    ).order_by('-total_amount')[:10]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'invoices': invoices[:100],
        
        # Summary
        'total_invoices': total_invoices,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'outstanding': outstanding,
        
        # Breakdowns
        'by_status': by_status,
        'overdue_count': overdue_count,
        'overdue_amount': overdue_amount,
        'top_customers': top_customers,
    }
    
    return render(request, 'reports/invoicing_report.html', context)
