"""
Workflow Services for Electricity Billing System
Handles all business logic and connections between models
"""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from decimal import Decimal
import random

from .models import (
    Customer, Contract, Meter, SubscriptionType, BillingPeriod,
    MeterReadingSubmission, MeterReading, Invoice, InvoiceLine, Payment,
    CustomerBalance, BalanceLedger, SMSQueue, SMSTemplate, InvoiceLineTemplate,
    InvoiceLineFormulaDetail, FinancialAdjustment
)


def record_financial_adjustment(data, user):
    """Record a financial adjustment and update customer balance/ledger"""
    customer_id = data.get('customer')
    customer = Customer.objects.get(pk=customer_id)
    adjustment_type = data.get('adjustment_type')
    amount = Decimal(data.get('amount', 0))
    reason = data.get('reason', '')
    
    with transaction.atomic():
        adjustment = FinancialAdjustment.objects.create(
            adjustment_number=generate_number('ADJ'),
            customer=customer,
            adjustment_type=adjustment_type,
            amount=amount,
            reason=reason,
            approved_by=user,
            approval_date=timezone.now(),
            is_approved=True
        )
        
        # Update balance
        # Debit increases balance (indebtedness), Credit decreases it
        debit = amount if adjustment_type == 'debit' else 0
        credit = amount if adjustment_type == 'credit' else 0
        
        customer.current_balance += (Decimal(debit) - Decimal(credit))
        customer.save()
        
        BalanceLedger.objects.create(
            customer=customer,
            transaction_type='adjustment',
            reference_id=adjustment.id,
            debit=debit,
            credit=credit,
            balance_after=customer.current_balance,
            notes=f'Adjustment {adjustment.adjustment_number}: {reason}',
            created_by=user
        )
        
    return adjustment


def generate_number(prefix, length=4):
    """Generate unique number with date prefix"""
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{random.randint(10**(length-1), 10**length-1)}"


def create_customer(data):
    """Create new customer with auto-generated number"""
    is_active = data.get('is_active')
    is_active = True if is_active == 'on' else False
    
    customer = Customer.objects.create(
        customer_number=data.get('customer_number') or generate_number('CUST'),
        full_name_ar=data['full_name_ar'],
        full_name_en=data.get('full_name_en', ''),
        national_id=data.get('national_id', ''),
        mobile_phone=data['mobile_phone'],
        phone2=data.get('phone2', ''),
        email=data.get('email', ''),
        address=data.get('address', ''),
        city=data.get('city', ''),
        credit_limit=data.get('credit_limit', 0),
        notes=data.get('notes', ''),
        is_active=is_active
    )
    
    CustomerBalance.objects.create(
        customer=customer,
        current_balance=0,
        credit_limit=customer.credit_limit
    )
    
    return customer


def create_contract(customer, data):
    """Create new contract for customer"""
    type_id = data.get('type')
    subscription_type = SubscriptionType.objects.get(pk=type_id) if type_id else None
    
    def parse_date(date_val):
        if not date_val:
            return None
        if isinstance(date_val, str):
            date_val = date_val.strip()
            if not date_val:
                return None
            from datetime import datetime as dt
            try:
                return dt.strptime(date_val, '%Y-%m-%d').date()
            except:
                return None
        return date_val
    
    end_date = parse_date(data.get('end_date'))
    start_date = parse_date(data.get('start_date')) or datetime.now().date()
    
    contract = Contract.objects.create(
        contract_number=data.get('contract_number') or generate_number('CTR'),
        customer=customer,
        type=subscription_type,
        start_date=start_date,
        end_date=end_date,
        contract_status=data.get('contract_status', 'active'),
        connection_load=data.get('connection_load', 0),
        deposit_amount=data.get('deposit_amount', 0),
        notes=data.get('notes', '')
    )
    return contract


def create_meter(contract, data):
    """Create new meter for contract"""
    last_reading = contract.meters.first()
    initial = last_reading.current_reading if last_reading else 0
    
    meter = Meter.objects.create(
        meter_number=data.get('meter_number') or generate_number('MTR'),
        contract=contract,
        meter_model=data.get('meter_model', ''),
        meter_type=data.get('meter_type', 'analog'),
        initial_reading=initial,
        installation_date=data.get('installation_date', datetime.now().date()),
        meter_status=data.get('meter_status', 'active'),
        location_description=data.get('location_description', '')
    )
    return meter


def submit_meter_reading(meter, data):
    """Submit a meter reading"""
    with transaction.atomic():
        previous = meter.last_approved_reading or 0
        
        reading_date = data.get('reading_date')
        if reading_date is None:
            from datetime import datetime as dt
            reading_date = dt.now().date()
        
        period = BillingPeriod.objects.filter(
            status__in=['reading_open', 'billing_in_progress'],
            start_date__lte=reading_date,
            end_date__gte=reading_date
        ).first()
        
        reader_id = data.get('reader_id')
        reader = User.objects.filter(pk=reader_id).first() if reader_id else None
        
        submission = MeterReadingSubmission.objects.create(
            meter=meter,
            contract=meter.contract,
            customer=meter.contract.customer,
            previous_reading=previous,
            submitted_reading=data.get('current_reading'),
            reading_date=reading_date,
            reader=reader,
            reader_notes=data.get('notes', ''),
            period=period
        )
        
        submission.meter.last_approved_reading = data.get('current_reading')
        submission.meter.save()
    
    return submission


def approve_reading(submission, approved_reading, user):
    """Approve meter reading and prepare for invoicing"""
    with transaction.atomic():
        submission.approval_status = 'approved'
        submission.reviewed_by = user
        submission.reviewed_at = timezone.now()
        submission.approved_reading = approved_reading
        submission.final_consumption = approved_reading - submission.previous_reading
        submission.save()
        
        MeterReading.objects.create(
            meter=submission.meter,
            reading_date=submission.reading_date,
            previous_reading=submission.previous_reading,
            current_reading=approved_reading,
            reading_source=submission.reading_source,
            reader=submission.reader,
            is_billed=False
        )
        
        submission.meter.last_reading_date = submission.reading_date
        submission.meter.save()
        
        if submission.contract:
            generate_invoice(submission)
    
    return submission


def generate_invoice(submission):
    """
    Generate invoice from approved reading
    Uses invoice line templates for calculation
    """
    contract = submission.contract
    customer = contract.customer
    
    consumption = submission.final_consumption
    if consumption is None:
        consumption = submission.submitted_reading - submission.previous_reading
    
    reading_date = submission.reading_date
    if reading_date is None:
        from datetime import datetime as dt
        reading_date = dt.now().date()
    
    with transaction.atomic():
        period = submission.period
        
        invoice = Invoice.objects.create(
            invoice_number=generate_number('INV'),
            contract=contract,
            subscription_type=contract.type,
            reading_id=None,
            period=period,
            issue_date=reading_date,
            due_date=reading_date + timedelta(days=15),
            total_amount=0,
            paid_amount=0,
            invoice_status='issued'
        )
        
        total = Decimal(0)
        
        earlier_unpaid = Invoice.objects.filter(
            contract=contract,
            issue_date__lt=reading_date,
            invoice_status__in=['issued', 'partially_paid', 'overdue']
        ).aggregate(prev=Sum('total_amount'))['prev'] or Decimal(0)
        
        earlier_paid = Invoice.objects.filter(
            contract=contract,
            issue_date__lt=reading_date,
            invoice_status__in=['issued', 'partially_paid', 'overdue']
        ).aggregate(paid=Sum('paid_amount'))['paid'] or Decimal(0)
        
        previous_indebtedness = earlier_unpaid - earlier_paid
        
        templates = InvoiceLineTemplate.objects.filter(
            type=contract.type,
            is_active=True
        ).order_by('line_order')
        
        for template in templates:
            if template.calculation_type != 'percentage':
                amount = calculate_line_amount(template, consumption)
            else:
                amount = Decimal(0)
            
            if template.calculation_type == 'single_rate_kwh':
                quantity = consumption
                rate = template.fixed_amount or Decimal(0)
            elif template.calculation_type == 'tiered_kwh':
                quantity = consumption
                rate = template.fixed_amount or Decimal(0)
            elif template.calculation_type == 'fixed':
                quantity = Decimal(1)
                rate = amount
            elif template.calculation_type == 'percentage':
                quantity = Decimal(1)
                rate = template.percentage_rate or Decimal(0)
            elif template.calculation_type == 'demand_charge':
                quantity = Decimal(1)
                rate = amount
            elif template.calculation_type == 'minimum_charge':
                quantity = Decimal(1)
                rate = amount
            else:
                quantity = Decimal(1)
                rate = amount
            
            InvoiceLine.objects.create(
                invoice=invoice,
                template=template,
                line_name_ar=template.line_name_ar,
                line_name_en=template.line_name_en,
                calculation_basis=str(template.calculation_type),
                quantity=quantity,
                rate=rate,
                amount=amount,
                line_order=template.line_order
            )
            total += amount
        
        # Second pass: recalculate percentage lines based on total of other lines
        total = InvoiceLine.objects.filter(invoice=invoice).aggregate(t=Sum('amount'))['t'] or Decimal(0)
        for line in InvoiceLine.objects.filter(invoice=invoice, template__calculation_type='percentage').order_by('line_order'):
            base_amount = total - line.amount
            line.amount = base_amount * (line.template.percentage_rate or Decimal(0)) / Decimal(100)
            line.save()
            total = InvoiceLine.objects.filter(invoice=invoice).aggregate(t=Sum('amount'))['t'] or Decimal(0)
        
        invoice.total_amount = total
        invoice.previous_indebtedness = previous_indebtedness
        invoice.save()
        
        customer.current_balance += total + previous_indebtedness
        customer.save()
        
        BalanceLedger.objects.create(
            customer=customer,
            transaction_type='invoice_created',
            reference_id=invoice.id,
            debit=total,
            credit=0,
            balance_after=customer.current_balance,
            notes=f'Invoice {invoice.invoice_number}'
        )
    
    return invoice


def calculate_line_amount(template, consumption):
    """Calculate line amount based on calculation type"""
    from decimal import Decimal
    
    if template.calculation_type == 'fixed':
        return template.fixed_amount or Decimal(0)
    
    elif template.calculation_type == 'single_rate_kwh':
        return (template.fixed_amount or Decimal(0)) * consumption
    
    elif template.calculation_type == 'tiered_kwh':
        # ✅ Correct Tiered Calculation
        total = Decimal(0)
        remaining = Decimal(consumption)
        # Order tiers by min_value to process them sequentially
        tiers = template.formula_details.all().order_by('min_value')
        
        if not tiers.exists():
            # Fallback to fixed_amount if no tiers are defined
            return (template.fixed_amount or Decimal(0)) * consumption

        for tier in tiers:
            if remaining <= 0:
                break
            
            tier_min = tier.min_value or Decimal(0)
            tier_max = tier.max_value or Decimal('999999999')
            
            # Range size for this tier
            tier_range = tier_max - tier_min
            
            # How much of the remaining consumption falls into this tier
            consumed_in_tier = min(remaining, tier_range)
            
            total += consumed_in_tier * (tier.rate_or_amount or Decimal(0))
            remaining -= consumed_in_tier
            
        return total
    
    elif template.calculation_type == 'percentage':
        # Percentage returns 0 in first pass; recalculated in second pass
        return Decimal(0)
    
    elif template.calculation_type in ('demand_charge', 'minimum_charge'):
        return template.fixed_amount or Decimal(0)
    
    return Decimal(0)


def record_payment(invoice, amount, data):
    """Record payment and update balances"""
    customer = invoice.contract.customer
    
    with transaction.atomic():
        payment = Payment.objects.create(
            payment_number=generate_number('PAY'),
            invoice=invoice,
            customer=customer,
            period=invoice.period,
            amount=amount,
            payment_method=data.get('payment_method', 'cash'),
            source_type=data.get('source_type', 'cash'),
            reference_number=data.get('reference_number', ''),
            bank_name=data.get('bank_name', ''),
            notes=data.get('notes', '')
        )
        
        invoice.paid_amount += amount
        if invoice.paid_amount >= invoice.total_amount:
            invoice.invoice_status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.invoice_status = 'partially_paid'
        invoice.save()
        
        BalanceLedger.objects.create(
            customer=customer,
            transaction_type='payment_received',
            reference_id=payment.id,
            debit=0,
            credit=amount,
            balance_after=customer.current_balance - amount,
            notes=f'Payment {payment.payment_number}'
        )
        
        customer.current_balance -= amount
        customer.save()
    
    return payment


def create_billing_period(data):
    """Create new billing period"""
    period = BillingPeriod.objects.create(
        period_name=data['period_name'],
        period_code=data.get('period_code') or f"{data['start_date'].strftime('%Y%m')}_MP",
        start_date=data['start_date'],
        end_date=data['end_date'],
        reading_start_date=data['reading_start_date'],
        reading_end_date=data['reading_end_date'],
        billing_cycle=data.get('billing_cycle', 'monthly'),
        status=data.get('status', 'reading_open')
    )
    return period


def send_sms(customer, template_type, context):
    """Send SMS to customer using template"""
    template = SMSTemplate.objects.filter(
        template_type=template_type,
        is_active=True
    ).first()
    
    if not template:
        return None
    
    message_content = template.content_template_ar
    for key, value in context.items():
        message_content = message_content.replace(f'{{{key}}}', str(value))
    
    sms = SMSQueue.objects.create(
        customer=customer,
        mobile_number=customer.mobile_phone,
        template=template,
        message_content=message_content,
        status='pending'
    )
    
    return sms


def get_customer_balance(customer):
    """Get customer balance details"""
    balance, _ = CustomerBalance.objects.get_or_create(customer=customer)
    return {
        'current': balance.current_balance,
        'credit_limit': balance.credit_limit,
        'available': balance.credit_limit - balance.current_balance
    }


def get_contract_readings(contract):
    """Get all readings for contract"""
    return MeterReading.objects.filter(
        meter__contract=contract
    ).order_by('-reading_date')


def get_contract_invoices(contract):
    """Get all invoices for contract"""
    return Invoice.objects.filter(
        contract=contract
    ).order_by('-issue_date')


def generate_invoices_for_period(period):
    """Generate invoices for all approved readings in a period"""
    return close_billing_period(period)


def close_billing_period(period):
    """Close billing period and generate all invoices"""
    from .models import BillingQueue
    
    submissions = MeterReadingSubmission.objects.filter(
        period=period,
        approval_status='approved'
    )
    
    invoices = []
    for submission in submissions:
        invoice = generate_invoice(submission)
        invoices.append(invoice)
        
        BillingQueue.objects.create(
            period=period,
            submission=submission,
            contract=submission.contract,
            customer=submission.customer,
            queue_status='completed',
            invoice=invoice,
            invoice_number=invoice.invoice_number
        )
    
    period.status = 'billing_completed'
    period.save()
    
    return invoices