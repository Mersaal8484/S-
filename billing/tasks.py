from celery import shared_task
from django_tenants.utils import schema_context
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


@shared_task
def generate_period_invoices_async(period_id, schema_name):
    with schema_context(schema_name):
        from billing.models import BillingPeriod
        from billing.services import close_billing_period
        period = BillingPeriod.objects.get(pk=period_id)
        close_billing_period(period)


@shared_task
def send_sms_queue():
    from billing.models import SMSQueue
    pending = SMSQueue.objects.filter(status='pending')[:50]
    for sms in pending:
        _send_single_sms(sms)


def _send_single_sms(sms):
    from billing.models import SMSProvider
    import requests
    provider = SMSProvider.objects.filter(is_active=True).first()
    if not provider:
        sms.status = 'failed'
        sms.error_message = 'No active SMS provider'
        sms.save()
        return

    try:
        resp = requests.post(provider.api_url, json={
            'to': sms.mobile_number,
            'message': sms.message_content,
            'sender': provider.sender_name,
        }, headers={
            'api_key': provider.api_key,
        }, timeout=10)
        sms.status = 'sent' if resp.ok else 'failed'
    except Exception as e:
        sms.status = 'failed'
        sms.error_message = str(e)
    sms.save()


@shared_task
def mark_overdue_invoices():
    from django_tenants.utils import get_tenant_model
    for tenant in get_tenant_model().objects.filter(is_active=True):
        with schema_context(tenant.schema_name):
            _mark_overdue_for_tenant()


def _mark_overdue_for_tenant():
    from billing.models import Invoice
    from datetime import date
    today = date.today()
    Invoice.objects.filter(
        due_date__lt=today,
        invoice_status__in=['issued', 'partially_paid']
    ).update(invoice_status='overdue')


@shared_task
def send_payment_reminders():
    from django_tenants.utils import get_tenant_model
    for tenant in get_tenant_model().objects.filter(is_active=True):
        with schema_context(tenant.schema_name):
            _send_reminders_for_tenant()


def _send_reminders_for_tenant():
    from billing.models import Invoice, SMSQueue, SMSTemplate, Customer
    from datetime import date
    today = date.today()
    due_soon = Invoice.objects.filter(
        due_date=today + timedelta(days=2),
        invoice_status__in=['issued', 'partially_paid']
    ).select_related('contract__customer')

    for invoice in due_soon:
        customer = invoice.contract.customer
        template = SMSTemplate.objects.filter(
            template_type='BillDueSoon', is_active=True
        ).first()
        if template:
            message = template.content_template_ar.replace('{invoice_number}', invoice.invoice_number)
            message = message.replace('{amount}', str(invoice.remaining_amount))
            SMSQueue.objects.create(
                customer=customer,
                mobile_number=customer.mobile_phone,
                template=template,
                message_content=message,
                status='pending',
            )
