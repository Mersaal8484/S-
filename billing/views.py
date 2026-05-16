from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.template.defaultfilters import date as date_filter
from django.views.decorators.clickjacking import xframe_options_sameorigin
import json


def to_decimal(value):
    try:
        return Decimal(str(value)) if value and value != '' else Decimal('0')
    except:
        return Decimal('0')


def to_bool(value):
    """Convert POST checkbox value to boolean"""
    if value is None:
        return False
    return value == 'on'


from django.contrib.auth.models import User

from .models import (
    Customer, Contract, Meter, SubscriptionType, BillingPeriod, MeterReadingSubmission,
    MeterReading, Invoice, InvoiceLine, Payment, Penalty, CustomerBalance, BalanceLedger,
    Collector, CollectorCashbox, Route, RouteContract, SMSProvider, SMSTemplate, SMSQueue,
    InvoiceLineTemplate, InvoiceLineFormulaDetail, SystemSettings
)
from .forms import CustomerForm, ContractForm, MeterForm, BillingPeriodForm, PaymentForm
from .services import generate_number
from . import services


def customer_list(request):
    customers = Customer.objects.all().order_by('customer_number')
    query = request.GET.get('q')
    if query:
        customers = customers.filter(
            Q(customer_number__icontains=query) |
            Q(full_name_ar__icontains=query) |
            Q(mobile_phone__icontains=query)
        )

    city = request.GET.get('city')
    if city:
        customers = customers.filter(city=city)

    cities = Customer.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city='')
    paginator = Paginator(customers, 25)
    page = request.GET.get('page')

    return render(request, 'billing/customer_list.html', {
        'customers': paginator.get_page(page),
        'cities': cities,
    })


def customer_create(request):
    if request.method == 'POST':
        try:
            customer = services.create_customer(request.POST)
            messages.success(request, 'Customer added successfully')
            return redirect('customer_detail', customer.id)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/customer_form.html', {
        'form': CustomerForm(),
        'title': 'إضافة مشترك'
    })


def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    contracts = customer.contracts.select_related('type').all()
    invoices = Invoice.objects.filter(contract__customer=customer).order_by('-created_at')[:10]
    payments = Payment.objects.filter(customer=customer).order_by('-payment_date')[:10]
    ledger = BalanceLedger.objects.filter(customer=customer).order_by('-transaction_date')[:20]

    return render(request, 'billing/customer_detail.html', {
        'customer': customer,
        'contracts': contracts,
        'invoices': invoices,
        'payments': payments,
        'ledger': ledger,
    })


def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated')
            return redirect('customer_detail', pk)
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'billing/customer_form.html', {
        'form': form,
        'title': 'تعديل بيانات المشترك'
    })


def contract_list(request):
    contracts = Contract.objects.select_related('customer', 'type').all()
    query = request.GET.get('q')
    if query:
        contracts = contracts.filter(
            Q(contract_number__icontains=query) |
            Q(customer__full_name_ar__icontains=query)
        )

    status = request.GET.get('status')
    if status:
        contracts = contracts.filter(contract_status=status)

    paginator = Paginator(contracts, 25)
    page = request.GET.get('page')

    return render(request, 'billing/contract_list.html', {
        'contracts': paginator.get_page(page),
    })


def contract_create(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, pk=customer_id)
        try:
            contract = services.create_contract(customer, request.POST)
            messages.success(request, 'Contract created')
            return redirect('contract_detail', contract.id)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/contract_form.html', {
        'form': ContractForm(),
        'title': 'إضافة عقد'
    })


def contract_detail(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    meters = contract.meters.all()
    invoices = contract.invoices.order_by('-created_at')[:10]
    readings = MeterReadingSubmission.objects.filter(contract=contract).order_by('-created_at')[:10]

    return render(request, 'billing/contract_detail.html', {
        'contract': contract,
        'meters': meters,
        'invoices': invoices,
        'readings': readings,
    })


def contract_update(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.save():
            messages.success(request, 'Contract updated')
            return redirect('contract_detail', pk)
    else:
        form = ContractForm(instance=contract)

    return render(request, 'billing/contract_form.html', {
        'form': form,
        'title': 'تعديل العقد'
    })


def meter_list(request):
    meters = Meter.objects.select_related('contract__customer').all()
    query = request.GET.get('q')
    if query:
        meters = meters.filter(
            Q(meter_number__icontains=query) |
            Q(contract__contract_number__icontains=query)
        )

    status = request.GET.get('status')
    if status:
        meters = meters.filter(meter_status=status)

    paginator = Paginator(meters, 25)
    page = request.GET.get('page')

    return render(request, 'billing/meter_list.html', {
        'meters': paginator.get_page(page),
    })


def meter_create(request):
    if request.method == 'POST':
        contract_id = request.POST.get('contract')
        contract = get_object_or_404(Contract, pk=contract_id)
        try:
            meter = services.create_meter(contract, request.POST)
            messages.success(request, 'Meter added')
            return redirect('meter_list')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/meter_form.html', {
        'form': MeterForm(),
        'title': 'إضافة عداد'
    })


def meter_edit(request, pk):
    meter = get_object_or_404(Meter, pk=pk)

    if request.method == 'POST':
        form = MeterForm(request.POST, instance=meter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Meter updated')
            return redirect('meter_list')
    else:
        form = MeterForm(instance=meter)

    return render(request, 'billing/meter_form.html', {
        'form': form,
        'title': 'تعديل العداد'
    })


def billing_period_list(request):
    periods = BillingPeriod.objects.order_by('-start_date')
    return render(request, 'billing/billing_period_list.html', {'periods': periods})


def billing_period_create(request):
    if request.method == 'POST':
        try:
            period = services.create_billing_period({
                'period_name': request.POST.get('period_name'),
                'start_date': datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date(),
                'end_date': datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date(),
                'reading_start_date': datetime.strptime(request.POST.get('reading_start_date'), '%Y-%m-%d').date(),
                'reading_end_date': datetime.strptime(request.POST.get('reading_end_date'), '%Y-%m-%d').date(),
                'billing_cycle': request.POST.get('billing_cycle', 'monthly'),
            })
            messages.success(request, 'Period created')
            return redirect('billing_period_list')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/billing_period_form.html', {
        'title': 'إضافة فترة'
    })


def billing_period_edit(request, pk):
    period = get_object_or_404(BillingPeriod, pk=pk)

    if request.method == 'POST':
        period.period_name = request.POST.get('period_name')
        period.period_code = request.POST.get('period_code')
        period.start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
        period.end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
        period.reading_start_date = datetime.strptime(request.POST.get('reading_start_date'), '%Y-%m-%d').date()
        period.reading_end_date = datetime.strptime(request.POST.get('reading_end_date'), '%Y-%m-%d').date()
        period.billing_cycle = request.POST.get('billing_cycle', 'monthly')
        period.status = request.POST.get('status')
        period.save()
        messages.success(request, 'Period updated')
        return redirect('billing_period_list')

    return render(request, 'billing/billing_period_form.html', {
        'title': 'تعديل الفترة',
        'period': period
    })


def reading_list(request):
    readings = MeterReadingSubmission.objects.select_related(
        'meter__contract__customer', 'customer'
    ).order_by('-created_at')

    query = request.GET.get('q')
    if query:
        readings = readings.filter(
            Q(meter__meter_number__icontains=query) |
            Q(customer__full_name_ar__icontains=query)
        )

    status = request.GET.get('status')
    if status:
        readings = readings.filter(approval_status=status)

    paginator = Paginator(readings, 25)
    page = request.GET.get('page')
    periods = BillingPeriod.objects.order_by('-start_date')[:10]

    return render(request, 'billing/reading_list.html', {
        'readings': paginator.get_page(page),
        'periods': periods,
    })


def reading_create(request):
    if request.method == 'POST':
        contract_id = request.POST.get('contract')
        contract = get_object_or_404(Contract, pk=contract_id)
        meter = contract.meters.filter(meter_status='active').first()
        if not meter:
            messages.error(request, 'No active meter for this contract')
            return redirect('reading_create')

        try:
            submission = services.submit_meter_reading(meter, {
                'current_reading': Decimal(request.POST.get('current_reading')),
                'reading_date': datetime.strptime(request.POST.get('reading_date'), '%Y-%m-%d').date(),
                'reader_id': request.POST.get('reader'),
                'notes': request.POST.get('notes', ''),
            })
            messages.success(request, 'Reading submitted')
            return redirect('reading_list')
        except Exception as e:
            messages.error(request, str(e))

    contracts = Contract.objects.filter(contract_status='active').select_related('customer')
    users = User.objects.filter(is_active=True)

    return render(request, 'billing/reading_form.html', {
        'title': 'تسجيل قراءة',
        'today': datetime.now().date().strftime('%Y-%m-%d'),
        'contracts': contracts,
        'users': users
    })


@login_required
def reading_approve(request, pk):
    reading = get_object_or_404(MeterReadingSubmission, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            try:
                services.approve_reading(reading, reading.submitted_reading, request.user)
                messages.success(request, 'Reading approved')
            except Exception as e:
                messages.error(request, str(e))
        else:
            reading.approval_status = 'rejected'
            reading.rejection_reason = request.POST.get('reason', '')
            reading.reviewed_by = request.user
            reading.reviewed_at = timezone.now()
            reading.save()
            messages.success(request, 'Reading rejected')

        return redirect('reading_list')

    return render(request, 'billing/reading_approve.html', {'reading': reading})


def invoice_list(request):
    invoices = Invoice.objects.select_related('contract__customer').order_by('-issue_date')
    query = request.GET.get('q')
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(contract__customer__full_name_ar__icontains=query)
        )

    paginator = Paginator(invoices, 25)
    page = request.GET.get('page')

    return render(request, 'billing/invoice_list.html', {
        'invoices': paginator.get_page(page),
    })


@login_required
def invoice_create(request):
    if request.method == 'POST':
        contract_id = request.POST.get('contract')
        reading_id = request.POST.get('reading')
        subscription_type_id = request.POST.get('subscription_type')
        period_id = request.POST.get('period')
        issue_date_str = request.POST.get('issue_date')
        due_date_str = request.POST.get('due_date')

        contract = get_object_or_404(Contract, pk=contract_id)
        reading = get_object_or_404(MeterReading, pk=reading_id) if reading_id else None
        subscription_type = get_object_or_404(SubscriptionType, pk=subscription_type_id) if subscription_type_id else None
        period = get_object_or_404(BillingPeriod, pk=period_id) if period_id else None

        issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else datetime.now().date()
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else issue_date + timedelta(days=15)

        consumption = reading.consumption if reading else Decimal(0)

        with transaction.atomic():
            invoice = Invoice.objects.create(
                invoice_number=generate_number('INV'),
                contract=contract,
                subscription_type=subscription_type,
                reading=reading,
                period=period,
                issue_date=issue_date,
                due_date=due_date,
                total_amount=0,
                paid_amount=0,
                invoice_status='issued'
            )

            total = Decimal(0)
            templates = InvoiceLineTemplate.objects.filter(
                type=subscription_type,
                is_active=True
            ).order_by('line_order')

            for template in templates:
                if template.calculation_type != 'percentage':
                    amount = services.calculate_line_amount(template, consumption or 0)
                else:
                    amount = Decimal(0)

                if template.calculation_type == 'single_rate_kwh':
                    quantity = consumption or Decimal(0)
                    rate = template.fixed_amount or Decimal(0)
                elif template.calculation_type == 'tiered_kwh':
                    quantity = consumption or Decimal(0)
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
                    rate = template.fixed_amount or Decimal(0)

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

            # Second pass: recalculate percentage lines
            total = InvoiceLine.objects.filter(invoice=invoice).aggregate(t=Sum('amount'))['t'] or Decimal(0)
            for line in InvoiceLine.objects.filter(invoice=invoice, template__calculation_type='percentage').order_by('line_order'):
                base_amount = total - line.amount
                line.amount = base_amount * (line.template.percentage_rate or Decimal(0)) / Decimal(100)
                line.save()
                total = InvoiceLine.objects.filter(invoice=invoice).aggregate(t=Sum('amount'))['t'] or Decimal(0)

            earlier_unpaid = Invoice.objects.filter(
                contract=contract,
                issue_date__lt=issue_date,
                invoice_status__in=['issued', 'partially_paid', 'overdue']
            ).aggregate(prev=Sum('total_amount'))['prev'] or Decimal(0)

            earlier_paid = Invoice.objects.filter(
                contract=contract,
                issue_date__lt=issue_date,
                invoice_status__in=['issued', 'partially_paid', 'overdue']
            ).aggregate(paid=Sum('paid_amount'))['paid'] or Decimal(0)

            invoice.total_amount = total
            invoice.previous_indebtedness = earlier_unpaid - earlier_paid
            invoice.save()

        messages.success(request, 'Invoice created')
        return redirect('invoice_detail', pk=invoice.id)

    contracts = Contract.objects.filter(contract_status='active').select_related('customer')
    subscription_types = SubscriptionType.objects.filter(is_active=True)
    periods = BillingPeriod.objects.filter(status__in=['reading_open', 'billing_in_progress', 'billing_completed']).order_by('-start_date')

    contract_readings = {}
    for contract in contracts:
        meters = contract.meters.all()
        readings = MeterReading.objects.filter(meter__in=meters).order_by('-reading_date')
        contract_readings[contract.id] = list(readings.values('id', 'previous_reading', 'current_reading', 'reading_date'))
        for r in contract_readings[contract.id]:
            r['consumption'] = str(r['current_reading'] - r['previous_reading'])
            r['previous_reading'] = str(r['previous_reading'])
            r['current_reading'] = str(r['current_reading'])
            r['reading_date'] = str(r['reading_date'])

    import json
    contract_readings_json = json.dumps(contract_readings)

    default_due = (datetime.now().date() + timedelta(days=15)).strftime('%Y-%m-%d')

    return render(request, 'billing/invoice_form.html', {
        'title': 'إنشاء فاتورة',
        'contracts': contracts,
        'subscription_types': subscription_types,
        'periods': periods,
        'today': datetime.now().date().strftime('%Y-%m-%d'),
        'default_due': default_due,
        'contract_readings_json': contract_readings_json,
    })


def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    lines = invoice.lines.all()
    payments = invoice.payments.all()
    penalties = invoice.penalties.all()

    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'lines': lines,
        'payments': payments,
        'penalties': penalties,
        'today_date': datetime.now().date(),
    })


@login_required
def invoice_regenerate(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    contract = invoice.contract

    if request.method == 'POST':
        reading_id = request.POST.get('reading')
        subscription_type_id = request.POST.get('subscription_type')
        period_id = request.POST.get('period')

        reading = get_object_or_404(MeterReading, pk=reading_id) if reading_id else None
        if subscription_type_id:
            invoice.subscription_type_id = subscription_type_id
        if period_id:
            invoice.period_id = period_id
        if reading_id:
            invoice.reading = reading
            consumption = reading.consumption
        else:
            consumption = Decimal(0)

        with transaction.atomic():
            invoice.lines.all().delete()
            invoice.invoice_status = 'issued'
            invoice.save()

            total = Decimal(0)
            templates = InvoiceLineTemplate.objects.filter(
                type=invoice.subscription_type,
                is_active=True
            ).order_by('line_order')

            for template in templates:
                if template.calculation_type != 'percentage':
                    amount = services.calculate_line_amount(template, consumption or 0)
                else:
                    amount = Decimal(0)

                if template.calculation_type == 'single_rate_kwh':
                    quantity = consumption or Decimal(0)
                    rate = template.fixed_amount or Decimal(0)
                elif template.calculation_type == 'tiered_kwh':
                    quantity = consumption or Decimal(0)
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
                    rate = template.fixed_amount or Decimal(0)

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

            # Second pass: recalculate percentage lines
            total = InvoiceLine.objects.filter(invoice=invoice).aggregate(t=Sum('amount'))['t'] or Decimal(0)
            for line in InvoiceLine.objects.filter(invoice=invoice, template__calculation_type='percentage').order_by('line_order'):
                base_amount = total - line.amount
                line.amount = base_amount * (line.template.percentage_rate or Decimal(0)) / Decimal(100)
                line.save()
                total = InvoiceLine.objects.filter(invoice=invoice).aggregate(t=Sum('amount'))['t'] or Decimal(0)

            earlier_unpaid = Invoice.objects.filter(
                contract=contract,
                issue_date__lt=invoice.issue_date,
                invoice_status__in=['issued', 'partially_paid', 'overdue']
            ).aggregate(prev=Sum('total_amount'))['prev'] or Decimal(0)

            earlier_paid = Invoice.objects.filter(
                contract=contract,
                issue_date__lt=invoice.issue_date,
                invoice_status__in=['issued', 'partially_paid', 'overdue']
            ).aggregate(paid=Sum('paid_amount'))['paid'] or Decimal(0)

            invoice.total_amount = total
            invoice.previous_indebtedness = earlier_unpaid - earlier_paid
            invoice.save()

        messages.success(request, 'Invoice regenerated')
        return redirect('invoice_detail', pk=pk)

    meters = contract.meters.all()
    readings = MeterReading.objects.filter(meter__in=meters).order_by('-reading_date')
    subscription_types = SubscriptionType.objects.filter(is_active=True)
    periods = BillingPeriod.objects.filter(status__in=['reading_open', 'billing_in_progress', 'billing_completed']).order_by('-start_date')

    return render(request, 'billing/invoice_regenerate.html', {
        'invoice': invoice,
        'readings': readings,
        'subscription_types': subscription_types,
        'periods': periods,
        'title': 'إعادة توليد الفاتورة',
    })


def invoice_print(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    customer = invoice.contract.customer

    previous_balance = float(invoice.previous_indebtedness)
    total_due = float(invoice.final_amount)

    return render(request, 'billing/invoice_print.html', {
        'invoice': invoice,
        'previous_balance': previous_balance,
        'total_due': total_due,
    })


def payment_list(request):
    payments = Payment.objects.select_related('customer', 'invoice').order_by('-payment_date')
    query = request.GET.get('q')
    if query:
        payments = payments.filter(
            Q(payment_number__icontains=query) |
            Q(customer__full_name_ar__icontains=query)
        )

    method = request.GET.get('method')
    if method:
        payments = payments.filter(payment_method=method)

    paginator = Paginator(payments, 25)
    page = request.GET.get('page')

    return render(request, 'billing/payment_list.html', {
        'payments': paginator.get_page(page),
    })


def payment_create(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        invoice_id = request.POST.get('invoice')
        contract_id = request.POST.get('contract')
        period_id = request.POST.get('period')
        period = get_object_or_404(BillingPeriod, pk=period_id) if period_id else None

        try:
            if invoice_id:
                invoice = get_object_or_404(Invoice, pk=invoice_id)
                payment = services.record_payment(invoice, amount, request.POST)
            elif contract_id:
                contract = get_object_or_404(Contract, pk=contract_id)
                payment = Payment.objects.create(
                    contract=contract,
                    customer=contract.customer,
                    period=period,
                    amount=amount,
                    payment_method=request.POST.get('payment_method', 'cash'),
                    reference_number=request.POST.get('reference_number', ''),
                    bank_name=request.POST.get('bank_name', ''),
                    notes=request.POST.get('notes', '')
                )
                contract.customer.current_balance -= amount
                contract.customer.save()
                BalanceLedger.objects.create(
                    customer=contract.customer,
                    transaction_type='payment_received',
                    reference_id=payment.id,
                    debit=0,
                    credit=amount,
                    balance_after=contract.customer.current_balance,
                    notes=f'Payment {payment.payment_number}'
                )
            else:
                customer_id = request.POST.get('customer')
                customer = get_object_or_404(Customer, pk=customer_id)
                payment = Payment.objects.create(
                    customer=customer,
                    period=period,
                    amount=amount,
                    payment_method=request.POST.get('payment_method', 'cash'),
                    reference_number=request.POST.get('reference_number', ''),
                    bank_name=request.POST.get('bank_name', ''),
                    notes=request.POST.get('notes', '')
                )
                customer.current_balance -= amount
                customer.save()
                BalanceLedger.objects.create(
                    customer=customer,
                    transaction_type='payment_received',
                    reference_id=payment.id,
                    debit=0,
                    credit=amount,
                    balance_after=customer.current_balance,
                    notes=f'Payment {payment.payment_number}'
                )
            messages.success(request, 'Payment recorded')
            return redirect('payment_list')
        except Exception as e:
            messages.error(request, str(e))

    invoices = Invoice.objects.filter(
        invoice_status__in=['issued', 'partially_paid', 'overdue']
    ).select_related('contract__customer')

    contracts = Contract.objects.filter(contract_status='active')
    customers = Customer.objects.filter(is_active=True)
    periods = BillingPeriod.objects.filter(status__in=['reading_open', 'billing_in_progress', 'billing_completed'])

    return render(request, 'billing/payment_form.html', {
        'title': 'تسجيل دفعة',
        'invoices': invoices,
        'contracts': contracts,
        'customers': customers,
        'periods': periods
    })


def payment_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'billing/payment_detail.html', {'payment': payment})


def collector_list(request):
    collectors = Collector.objects.all()
    return render(request, 'billing/collector_list.html', {'collectors': collectors})


def collector_create(request):
    if request.method == 'POST':
        full_name_ar = (request.POST.get('full_name_ar') or '').strip()
        if not full_name_ar:
            messages.error(request, 'Collector name is required')
            return render(request, 'billing/collector_form.html', {'title': 'إضافة محصل'})

        from datetime import date
        Collector.objects.create(
            collector_code=generate_number('COL'),
            full_name_ar=full_name_ar,
            full_name_en=request.POST.get('full_name_en', ''),
            national_id=request.POST.get('national_id', ''),
            mobile_phone=request.POST.get('mobile_phone', ''),
            email=request.POST.get('email', ''),
            hire_date=date.today(),
            commission_percent=to_decimal(request.POST.get('commission_percent')),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Collector created')
        return redirect('collector_list')

    return render(request, 'billing/collector_form.html', {'title': 'إضافة محصل'})


def route_list(request):
    routes = Route.objects.all()
    return render(request, 'billing/route_list.html', {'routes': routes})


def route_create(request):
    if request.method == 'POST':
        route = Route.objects.create(
            route_name_ar=request.POST.get('route_name_ar'),
            route_name_en=request.POST.get('route_name_en'),
            route_type=request.POST.get('route_type', 'meter_reading'),
            region=request.POST.get('region', ''),
            area_description=request.POST.get('area_description', ''),
        )
        messages.success(request, 'Route created')
        return redirect('route_list')

    return render(request, 'billing/route_form.html', {'title': 'إضافة مسار'})


def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    route_contracts = route.contracts.select_related('contract__customer').order_by('stop_order')
    available_contracts = Contract.objects.filter(
        contract_status='active'
    ).exclude(
        id__in=route_contracts.values('contract_id')
    ).select_related('customer')

    return render(request, 'billing/route_detail.html', {
        'route': route,
        'route_contracts': route_contracts,
        'available_contracts': available_contracts
    })


def route_add_contract(request, route_id):
    route = get_object_or_404(Route, pk=route_id)
    if request.method == 'POST':
        contract_id = request.POST.get('contract')
        contract = get_object_or_404(Contract, pk=contract_id)
        stop_order = request.POST.get('stop_order', 0)

        RouteContract.objects.create(
            route=route,
            contract=contract,
            stop_order=stop_order or route.contracts.count() + 1
        )
        messages.success(request, 'Contract added to route')

    return redirect('route_detail', pk=route_id)


def route_remove_contract(request, route_id, contract_id):
    route = get_object_or_404(Route, pk=route_id)
    rc = get_object_or_404(RouteContract, route=route, contract_id=contract_id)
    rc.delete()
    messages.success(request, 'Contract removed from route')
    return redirect('route_detail', pk=route_id)


def sms_list(request):
    messages = SMSQueue.objects.select_related('customer').order_by('-created_at')
    status = request.GET.get('status')
    if status:
        messages = messages.filter(status=status)

    paginator = Paginator(messages, 25)
    page = request.GET.get('page')

    return render(request, 'billing/sms_list.html', {
        'messages': paginator.get_page(page),
    })


def sms_create(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, pk=customer_id)
        message = request.POST.get('message')
        template_id = request.POST.get('template')
        template = SMSTemplate.objects.filter(pk=template_id).first() if template_id else None

        SMSQueue.objects.create(
            customer=customer,
            mobile_number=customer.mobile_phone,
            message_content=message,
            template=template,
            status='pending'
        )
        messages.success(request, 'SMS queued')
        return redirect('sms_list')

    customers = Customer.objects.filter(is_active=True)
    templates = SMSTemplate.objects.filter(is_active=True)
    return render(request, 'billing/sms_form.html', {'customers': customers, 'templates': templates})


def sms_provider_list(request):
    providers = SMSProvider.objects.all()
    return render(request, 'billing/sms_provider_list.html', {'providers': providers})


def sms_provider_create(request):
    if request.method == 'POST':
        SMSProvider.objects.create(
            provider_name=request.POST.get('provider_name'),
            api_url=request.POST.get('api_url'),
            api_key=request.POST.get('api_key'),
            sender_name=request.POST.get('sender_name'),
            country_code=request.POST.get('country_code', '966'),
            is_active=True
        )
        messages.success(request, 'Provider created')
        return redirect('sms_provider_list')

    return render(request, 'billing/sms_provider_form.html')


def sms_template_list(request):
    templates = SMSTemplate.objects.all()
    return render(request, 'billing/sms_template_list.html', {'templates': templates})


def sms_template_create(request):
    if request.method == 'POST':
        SMSTemplate.objects.create(
            template_type=request.POST.get('template_type'),
            title_ar=request.POST.get('title_ar'),
            content_template_ar=request.POST.get('content_template_ar'),
            language=request.POST.get('language', 'ar'),
            is_active=True
        )
        messages.success(request, 'Template created')
        return redirect('sms_template_list')

    return render(request, 'billing/sms_template_form.html')


def sms_template_edit(request, pk):
    template = get_object_or_404(SMSTemplate, pk=pk)

    if request.method == 'POST':
        template.template_type = request.POST.get('template_type')
        template.title_ar = request.POST.get('title_ar')
        template.content_template_ar = request.POST.get('content_template_ar')
        template.language = request.POST.get('language', 'ar')
        template.is_active = request.POST.get('is_active') == 'on'
        template.save()
        messages.success(request, 'Template updated')
        return redirect('sms_template_list')

    return render(request, 'billing/sms_template_form.html', {'template': template})





def close_period(request, pk):
    period = get_object_or_404(BillingPeriod, pk=pk)
    try:
        invoices = services.close_billing_period(period)
        messages.success(request, f'Generated {len(invoices)} invoices')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('billing_period_list')


def system_settings(request):
    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()

    subscription_types = SubscriptionType.objects.all()

    # Group templates by subscription type
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

    # Convert to JSON for JavaScript
    templates_by_type_json = json.dumps(templates_by_type)

    if request.method == 'POST':
        settings_obj.company_name = request.POST.get('company_name', '')
        settings_obj.company_address = request.POST.get('company_address', '')
        settings_obj.phone = request.POST.get('phone', '')
        settings_obj.email = request.POST.get('email', '')
        settings_obj.vat_number = request.POST.get('vat_number', '')
        settings_obj.save()
        messages.success(request, 'Settings saved')
        if request.POST.get('next'):
            return redirect(request.POST.get('next'))
        return redirect('system_settings')

    return render(request, 'billing/settings.html', {
        'settings': settings_obj,
        'subscription_types': subscription_types,
        'templates_by_type': templates_by_type,
        'templates_by_type_json': templates_by_type_json,
    })


def subscription_type_create(request):
    if request.method == 'POST':
        SubscriptionType.objects.create(
            name_ar=request.POST.get('name_ar'),
            name_en=request.POST.get('name_en', ''),
            description=request.POST.get('description', ''),
            is_active=to_bool(request.POST.get('is_active'))
        )
        messages.success(request, 'Subscription type created')
        return redirect('system_settings')
    return render(request, 'billing/subscription_type_form.html', {'title': 'إضافة نوع اشتراك'})


def subscription_type_edit(request, pk):
    st = get_object_or_404(SubscriptionType, pk=pk)
    if request.method == 'POST':
        st.name_ar = request.POST.get('name_ar')
        st.name_en = request.POST.get('name_en', '')
        st.description = request.POST.get('description', '')
        st.is_active = to_bool(request.POST.get('is_active'))
        st.save()
        messages.success(request, 'Subscription type updated')
        return redirect('system_settings')
    return render(request, 'billing/subscription_type_form.html', {'title': 'تعديل نوع الاشتراك', 'type': st})


def template_create(request, type_id=None):
    subscription_types = SubscriptionType.objects.all()

    if request.method == 'POST':
        type_id = request.POST.get('type') or type_id
        try:
            template = InvoiceLineTemplate.objects.create(
                type_id=type_id,
                line_order=request.POST.get('line_order', 0),
                line_name_ar=request.POST.get('line_name_ar'),
                line_name_en=request.POST.get('line_name_en', ''),
                calculation_type=request.POST.get('calculation_type'),
                fixed_amount=to_decimal(request.POST.get('fixed_amount')),
                percentage_rate=to_decimal(request.POST.get('percentage_rate'))
            )

            # Create formula details for tiered kwh
            if template.calculation_type == 'tiered_kwh':
                # Create default tiers
                tiers = [
                    (0, 100, 0.08),
                    (101, 300, 0.12),
                    (301, 600, 0.18),
                    (601, None, 0.25),
                ]
                for min_v, max_v, rate in tiers:
                    InvoiceLineFormulaDetail.objects.create(
                        template=template,
                        min_value=min_v,
                        max_value=max_v,
                        rate_or_amount=rate,
                        is_rate_per_kwh=True
                    )
            elif template.calculation_type == 'fixed':
                InvoiceLineFormulaDetail.objects.create(
                    template=template,
                    min_value=0,
                    max_value=None,
                    rate_or_amount=request.POST.get('fixed_amount', 0),
                    is_rate_per_kwh=False
                )
            elif template.calculation_type == 'percentage':
                InvoiceLineFormulaDetail.objects.create(
                    template=template,
                    min_value=None,
                    max_value=None,
                    rate_or_amount=request.POST.get('percentage_rate', 0),
                    is_rate_per_kwh=False
                )

            messages.success(request, 'Template created')
            return redirect('system_settings')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/template_form.html', {
        'title': 'إضافة نموذج',
        'subscription_types': subscription_types,
        'selected_type': type_id
    })


def template_list(request):
    templates = InvoiceLineTemplate.objects.select_related('type').order_by('type', 'line_order')
    return render(request, 'billing/template_list.html', {'templates': templates})


def template_delete(request, pk):
    template = get_object_or_404(InvoiceLineTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Template deleted')
        return redirect('system_settings')
    return render(request, 'billing/template_confirm_delete.html', {'template': template})


def template_detail(request, pk):
    template = get_object_or_404(InvoiceLineTemplate, pk=pk)
    details = template.formula_details.all()

    if request.method == 'POST':
        # Add new formula detail
        min_val = request.POST.get('min_value')
        max_val = request.POST.get('max_value')
        rate = request.POST.get('rate_or_amount')
        is_rate = request.POST.get('is_rate_per_kwh') == 'on'

        if min_val and rate:
            InvoiceLineFormulaDetail.objects.create(
                template=template,
                min_value=int(min_val) if min_val else None,
                max_value=int(max_val) if max_val else None,
                rate_or_amount=rate,
                is_rate_per_kwh=is_rate
            )
            messages.success(request, 'Formula added')
            return redirect('template_detail', pk=pk)

    return render(request, 'billing/template_detail.html', {
        'template': template,
        'details': details
    })


def template_create_for_type(request, type_id):
    """Create template for specific subscription type"""
    subscription_type = get_object_or_404(SubscriptionType, pk=type_id)
    subscription_types = SubscriptionType.objects.all()

    if request.method == 'POST':
        try:
            template = InvoiceLineTemplate.objects.create(
                type=subscription_type,
                line_order=request.POST.get('line_order', 0),
                line_name_ar=request.POST.get('line_name_ar'),
                line_name_en=request.POST.get('line_name_en', ''),
                calculation_type=request.POST.get('calculation_type'),
                fixed_amount=to_decimal(request.POST.get('fixed_amount')),
                percentage_rate=to_decimal(request.POST.get('percentage_rate'))
            )

            # Create formula details for tiered kWh
            if template.calculation_type == 'tiered_kwh':
                tiers = [
                    (0, 100, 0.08),
                    (101, 300, 0.12),
                    (301, 600, 0.18),
                    (601, None, 0.25),
                ]
                for min_v, max_v, rate in tiers:
                    InvoiceLineFormulaDetail.objects.create(
                        template=template,
                        min_value=min_v,
                        max_value=max_v,
                        rate_or_amount=rate,
                        is_rate_per_kwh=True
                    )
            elif template.calculation_type == 'fixed':
                InvoiceLineFormulaDetail.objects.create(
                    template=template,
                    min_value=0,
                    max_value=None,
                    rate_or_amount=request.POST.get('fixed_amount', 0),
                    is_rate_per_kwh=False
                )
            elif template.calculation_type == 'percentage':
                InvoiceLineFormulaDetail.objects.create(
                    template=template,
                    min_value=None,
                    max_value=None,
                    rate_or_amount=request.POST.get('percentage_rate', 0),
                    is_rate_per_kwh=False
                )

            messages.success(request, 'Template created')
            return redirect('system_settings')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/template_form.html', {
        'title': f'إضافة نموذج لـ {subscription_type.name_ar}',
        'subscription_types': subscription_types,
        'selected_type': type_id,
})


def template_edit(request, pk):
    template = get_object_or_404(InvoiceLineTemplate, pk=pk)
    subscription_types = SubscriptionType.objects.all()

    if request.method == 'POST':
        try:
            template.type_id = request.POST.get('type')
            template.line_order = request.POST.get('line_order', template.line_order)
            template.line_name_ar = request.POST.get('line_name_ar')
            template.line_name_en = request.POST.get('line_name_en', '')
            template.calculation_type = request.POST.get('calculation_type')
            template.fixed_amount = to_decimal(request.POST.get('fixed_amount'))
            template.percentage_rate = to_decimal(request.POST.get('percentage_rate'))
            template.save()
            messages.success(request, 'Template updated')
            return redirect('system_settings')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'billing/template_form.html', {
        'title': 'تعديل النموذج',
        'template': template,
        'subscription_types': subscription_types,
    })


def ledger_list(request):
    ledger = BalanceLedger.objects.select_related('customer').order_by('-transaction_date')
    customer_id = request.GET.get('customer')
    if customer_id:
        ledger = ledger.filter(customer_id=customer_id)

    transaction_type = request.GET.get('type')
    if transaction_type:
        ledger = ledger.filter(transaction_type=transaction_type)

    paginator = Paginator(ledger, 25)
    page = request.GET.get('page')

    customers = Customer.objects.all()

    return render(request, 'billing/ledger_list.html', {
        'ledger': paginator.get_page(page),
        'customers': customers
    })


def ledger_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    ledger = BalanceLedger.objects.filter(customer=customer).order_by('-transaction_date')

    total_debit = ledger.aggregate(Sum('debit'))['debit__sum'] or 0
    total_credit = ledger.aggregate(Sum('credit'))['credit__sum'] or 0

    return render(request, 'billing/ledger_detail.html', {
        'customer': customer,
        'ledger': ledger,
        'total_debit': total_debit,
        'total_credit': total_credit,
    })


def adjustment_create(request):
    if request.method == 'POST':
        try:
            services.record_financial_adjustment(request.POST, request.user)
            messages.success(request, 'تم تسجيل التسوية المالية بنجاح')
            return redirect('ledger_list')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    customers = Customer.objects.filter(is_active=True)
    return render(request, 'billing/adjustment_form.html', {
        'title': 'تسجيل تسوية مالية',
        'customers': customers
    })


@login_required
def consumption_adjustment(request):
    """View to adjust meter readings"""
    if request.method == 'POST':
        meter_id = request.POST.get('meter')
        new_reading = Decimal(request.POST.get('new_reading', '0'))
        reason = request.POST.get('reason')

        meter = get_object_or_404(Meter, pk=meter_id)

        with transaction.atomic():
            old_reading = meter.last_approved_reading or meter.initial_reading
            meter.last_approved_reading = new_reading
            meter.save()

            # Record as an approved submission for history
            MeterReadingSubmission.objects.create(
                meter=meter,
                contract=meter.contract,
                customer=meter.contract.customer,
                previous_reading=old_reading,
                submitted_reading=new_reading,
                approved_reading=new_reading,
                approval_status='approved',
                reading_source='estimated',
                reader_notes=f"تعديل استهلاك: {reason}",
                reviewed_by=request.user,
                reviewed_at=timezone.now()
            )

        messages.success(request, 'تم تعديل قراءة العداد بنجاح')
        return redirect('meter_list')

    meters = Meter.objects.select_related('contract__customer').filter(meter_status='active')
    return render(request, 'billing/consumption_adjustment.html', {
        'meters': meters
    })


@login_required
def billing_reports_view(request):
    """Detailed financial and operational reports dashboard for billing"""
    # Summary stats
    stats = {
        'total_revenue': Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_outstanding': sum(float(inv.total_amount) - float(inv.paid_amount) for inv in Invoice.objects.filter(invoice_status__in=['issued', 'partially_paid', 'overdue'])),
        'active_contracts': Contract.objects.filter(contract_status='active').count(),
        'pending_readings': MeterReadingSubmission.objects.filter(approval_status='pending').count(),
    }

    # Revenue by month (last 6 months)
    revenue_history = []
    for i in range(6):
        date = timezone.now() - timedelta(days=30*i)
        month_revenue = Payment.objects.filter(payment_date__year=date.year, payment_date__month=date.month).aggregate(Sum('amount'))['amount__sum'] or 0
        revenue_history.append({
            'month': date.strftime('%b'),
            'amount': month_revenue
        })
    revenue_history.reverse()

    return render(request, 'billing/reports.html', {
        'stats': stats,
        'revenue_history': revenue_history
    })
