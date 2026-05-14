from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    Contract, ContractLine, MeterReading, DateRange, DateRangeType,
    UoM, UoMCategory, Journal, InvoiceTemplate, TaskQueue, Product
)
from .forms import (
    ContractForm, ContractLineForm, MeterReadingForm, DateRangeForm,
    DateRangeTypeForm, UoMForm, JournalForm, InvoiceTemplateForm, TaskQueueForm
)
from billing.models import Customer


def _get_contract_types():
    return ContractLine.CONTRACT_TYPE_CHOICES


def _get_pricing_types():
    return InvoiceTemplate.PRICING_TYPE_CHOICES


@login_required
def contract_list(request):
    contracts = Contract.objects.select_related('partner', 'journal').all()
    query = request.GET.get('q')
    if query:
        contracts = contracts.filter(
            Q(contract_number__icontains=query) |
            Q(name__icontains=query) |
            Q(partner_old_id__icontains=query) |
            Q(meter_number__icontains=query) |
            Q(partner__full_name_ar__icontains=query)
        )
    paginator = Paginator(contracts, 25)
    page = request.GET.get('page')
    return render(request, 'contract_management/contract_list.html', {
        'contracts': paginator.get_page(page),
    })


@login_required
def contract_create(request):
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save()
            messages.success(request, 'Contract created successfully')
            return redirect('contract_detail', pk=contract.pk)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ContractForm()

    customers = Customer.objects.filter(is_active=True)
    journals = Journal.objects.filter(is_active=True)
    return render(request, 'contract_management/contract_form.html', {
        'form': form,
        'title': 'Create Contract',
        'contract': None,
        'customers': customers,
        'journals': journals,
    })


@login_required
def contract_detail(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    lines = ContractLine.objects.filter(contract=contract).select_related('product', 'uom')
    readings = MeterReading.objects.filter(contract=contract).order_by('-reading_date')
    return render(request, 'contract_management/contract_detail.html', {
        'contract': contract,
        'lines': lines,
        'readings': readings,
    })


@login_required
def contract_edit(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contract updated successfully')
            return redirect('contract_detail', pk=contract.pk)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ContractForm(instance=contract)

    customers = Customer.objects.filter(is_active=True)
    journals = Journal.objects.filter(is_active=True)
    return render(request, 'contract_management/contract_form.html', {
        'form': form,
        'title': 'Edit Contract',
        'contract': contract,
        'customers': customers,
        'journals': journals,
    })


@login_required
def contract_delete(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        contract.is_active = False
        contract.save()
        messages.success(request, 'Contract deactivated successfully')
        return redirect('contract_list')
    return render(request, 'contract_management/confirm_delete.html', {
        'object': contract,
        'type': 'Contract',
    })


@login_required
def contract_line_create(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk)
    if request.method == 'POST':
        form = ContractLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.contract = contract
            line.save()
            messages.success(request, 'Line added successfully')
            return redirect('contract_detail', pk=contract.pk)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ContractLineForm()

    products = Product.objects.filter(is_active=True)
    uoms = UoM.objects.filter(is_active=True)
    return render(request, 'contract_management/line_form.html', {
        'form': form,
        'title': 'Add Invoice Line',
        'contract': contract,
        'products': products,
        'uoms': uoms,
        'contract_types': _get_contract_types(),
    })


@login_required
def contract_line_delete(request, pk):
    line = get_object_or_404(ContractLine, pk=pk)
    contract_pk = line.contract_id
    if request.method == 'POST':
        line.delete()
        messages.success(request, 'Line deleted successfully')
        return redirect('contract_detail', pk=contract_pk)
    return render(request, 'contract_management/confirm_delete.html', {
        'object': line,
        'type': 'Contract Line',
    })


@login_required
def contract_invoice_create(request, pk):
    contract = get_object_or_404(Contract, pk=pk)

    readings = MeterReading.objects.filter(contract=contract, is_invoiced=False).order_by('reading_date')
    if not readings.exists():
        messages.warning(request, 'No un-invoiced readings found')
        return redirect('contract_detail', pk=pk)

    lines = ContractLine.objects.filter(contract=contract, is_active=True)
    if not lines.exists():
        messages.warning(request, 'No invoice lines configured for this contract')
        return redirect('contract_detail', pk=pk)

    total_consumption = sum(r.consumption for r in readings if r.consumption > 0)

    total = Decimal(0)
    invoice_lines_data = []
    for line in lines:
        amt = line.amount
        total += amt
        invoice_lines_data.append({
            'name': line.product.name if line.product else line.description,
            'quantity': line.quantity,
            'rate': line.unit_price,
            'amount': amt,
        })

    try:
        from billing.models import Invoice as BillingInvoice
        from billing.models import InvoiceLine as BillingInvoiceLine
        from billing.models import Contract as BillingContract
        from billing.models import SubscriptionType

        customer = contract.partner
        if not customer:
            messages.error(request, 'Contract has no customer assigned')
            return redirect('contract_detail', pk=pk)

        sub_type, _ = SubscriptionType.objects.get_or_create(
            name_ar='General',
            defaults={'name_en': 'General', 'is_active': True}
        )

        billing_contract, _ = BillingContract.objects.get_or_create(
            customer=customer,
            defaults={
                'type': sub_type,
                'contract_number': f'AUTO-{contract.contract_number or contract.pk}',
                'contract_status': 'active',
            }
        )

        with transaction.atomic():
            invoice = BillingInvoice.objects.create(
                contract=billing_contract,
                subscription_type=sub_type,
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=15),
                total_amount=total,
                invoice_status='issued',
            )

            for ld in invoice_lines_data:
                BillingInvoiceLine.objects.create(
                    invoice=invoice,
                    line_name_ar=ld['name'],
                    quantity=ld['quantity'],
                    rate=ld['rate'],
                    amount=ld['amount'],
                )

            readings.update(is_invoiced=True)

            last_reading = readings.last()
            if last_reading:
                contract.meter_last_invoice_reading = last_reading.current_reading
                contract.save()

        messages.success(request, f'Invoice {invoice.invoice_number} created successfully')
        return redirect('billing:invoice_detail', pk=invoice.pk)

    except Exception as e:
        messages.error(request, f'Error creating invoice: {str(e)}')
        return redirect('contract_detail', pk=pk)


@login_required
def meter_reading_create(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk)
    if request.method == 'POST':
        form = MeterReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.contract = contract
            reading.save()
            contract.meter_current_reading = reading.current_reading
            contract.save()
            messages.success(request, 'Meter reading added successfully')
            return redirect('contract_detail', pk=contract.pk)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = MeterReadingForm()

    return render(request, 'contract_management/reading_form.html', {
        'form': form,
        'title': 'Add Meter Reading',
        'contract': contract,
    })


@login_required
def meter_reading_delete(request, pk):
    reading = get_object_or_404(MeterReading, pk=pk)
    contract_pk = reading.contract_id
    if request.method == 'POST':
        reading.delete()
        messages.success(request, 'Reading deleted successfully')
        return redirect('contract_detail', pk=contract_pk)
    return render(request, 'contract_management/confirm_delete.html', {
        'object': reading,
        'type': 'Meter Reading',
    })


@login_required
def date_range_list(request):
    ranges = DateRange.objects.select_related('date_range_type').all()
    query = request.GET.get('q')
    if query:
        ranges = ranges.filter(
            Q(name__icontains=query) |
            Q(date_range_type__name__icontains=query)
        )
    paginator = Paginator(ranges, 25)
    page = request.GET.get('page')
    return render(request, 'contract_management/date_range_list.html', {
        'ranges': paginator.get_page(page),
    })


@login_required
def date_range_type_list(request):
    types = DateRangeType.objects.all()
    return render(request, 'contract_management/date_range_type_list.html', {
        'types': types,
    })


@login_required
def invoice_template_list(request):
    templates = InvoiceTemplate.objects.select_related('product', 'uom').all()
    contract_type = request.GET.get('type')
    if contract_type:
        templates = templates.filter(contract_type=contract_type)
    return render(request, 'contract_management/invoice_template_list.html', {
        'templates': templates,
        'contract_types': _get_contract_types(),
    })


@login_required
def invoice_template_create(request):
    if request.method == 'POST':
        form = InvoiceTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Invoice template created successfully')
            return redirect('invoice_template_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = InvoiceTemplateForm()

    products = Product.objects.filter(is_active=True)
    uoms = UoM.objects.filter(is_active=True)
    return render(request, 'contract_management/invoice_template_form.html', {
        'form': form,
        'title': 'Create Invoice Template',
        'template': None,
        'products': products,
        'uoms': uoms,
        'contract_types': _get_contract_types(),
    })


@login_required
def invoice_template_edit(request, pk):
    template = get_object_or_404(InvoiceTemplate, pk=pk)
    if request.method == 'POST':
        form = InvoiceTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Invoice template updated successfully')
            return redirect('invoice_template_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = InvoiceTemplateForm(instance=template)

    products = Product.objects.filter(is_active=True)
    uoms = UoM.objects.filter(is_active=True)
    return render(request, 'contract_management/invoice_template_form.html', {
        'form': form,
        'title': 'Edit Invoice Template',
        'template': template,
        'products': products,
        'uoms': uoms,
        'contract_types': _get_contract_types(),
    })


@login_required
def journal_list(request):
    journals = Journal.objects.all()
    return render(request, 'contract_management/journal_list.html', {
        'journals': journals,
    })


@login_required
def uom_list(request):
    uoms = UoM.objects.select_related('category').all()
    return render(request, 'contract_management/uom_list.html', {
        'uoms': uoms,
    })


@login_required
def uom_create(request):
    if request.method == 'POST':
        form = UoMForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'UoM created successfully')
            return redirect('uom_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = UoMForm()

    return render(request, 'contract_management/uom_form.html', {
        'form': form,
        'title': 'Create Unit of Measure',
    })


@login_required
def task_queue_list(request):
    tasks = TaskQueue.objects.all()
    query = request.GET.get('q')
    if query:
        tasks = tasks.filter(
            Q(name__icontains=query) |
            Q(task_type__icontains=query)
        )
    status = request.GET.get('status')
    if status:
        tasks = tasks.filter(status=status)
    paginator = Paginator(tasks, 25)
    page = request.GET.get('page')
    return render(request, 'contract_management/task_queue_list.html', {
        'tasks': paginator.get_page(page),
    })


@login_required
def task_queue_create(request):
    if request.method == 'POST':
        form = TaskQueueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task enqueued successfully')
            return redirect('task_queue_list')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = TaskQueueForm()

    return render(request, 'contract_management/task_form.html', {
        'form': form,
        'title': 'Create Task',
    })


@login_required
def process_recurring_invoices(request):
    today = timezone.now().date()
    contracts = Contract.objects.filter(
        is_active=True,
        recurring_invoices=True,
        recurring_next_date__lte=today,
    )

    processed = 0
    for contract in contracts:
        try:
            lines = ContractLine.objects.filter(contract=contract, is_active=True)
            if not lines.exists():
                continue

            readings = MeterReading.objects.filter(contract=contract, is_invoiced=False).order_by('reading_date')
            if not readings.exists():
                continue

            total = Decimal(0)
            for line in lines:
                total += line.amount

            customer = contract.partner
            if not customer:
                continue

            from billing.models import Invoice as BillingInvoice
            from billing.models import InvoiceLine as BillingInvoiceLine
            from billing.models import Contract as BillingContract
            from billing.models import SubscriptionType

            sub_type, _ = SubscriptionType.objects.get_or_create(
                name_ar='General',
                defaults={'name_en': 'General', 'is_active': True}
            )

            billing_contract, _ = BillingContract.objects.get_or_create(
                customer=customer,
                defaults={
                    'type': sub_type,
                    'contract_number': f'AUTO-{contract.contract_number or contract.pk}',
                    'contract_status': 'active',
                }
            )

            with transaction.atomic():
                invoice = BillingInvoice.objects.create(
                    contract=billing_contract,
                    subscription_type=sub_type,
                    issue_date=today,
                    due_date=today + timedelta(days=15),
                    total_amount=total,
                    invoice_status='issued',
                )

                for line in lines:
                    BillingInvoiceLine.objects.create(
                        invoice=invoice,
                        line_name_ar=line.product.name if line.product else line.description,
                        quantity=line.quantity,
                        rate=line.unit_price,
                        amount=line.amount,
                    )

                readings.update(is_invoiced=True)

                last_reading = readings.last()
                if last_reading:
                    contract.meter_last_invoice_reading = last_reading.current_reading

                from dateutil.relativedelta import relativedelta
                rule_map = {
                    'daily': relativedelta(days=contract.recurring_interval),
                    'weekly': relativedelta(weeks=contract.recurring_interval),
                    'monthly': relativedelta(months=contract.recurring_interval),
                    'yearly': relativedelta(years=contract.recurring_interval),
                }
                delta = rule_map.get(contract.recurring_rule_type, relativedelta(months=1))
                contract.recurring_next_date = today + delta
                contract.save()

            processed += 1

        except Exception:
            continue

    messages.success(request, f'Processed {processed} recurring invoice(s)')
    return redirect('task_queue_list')
