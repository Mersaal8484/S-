from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from .models import (
    Account, Vendor, Customer, Product, JournalEntry, JournalLine,
    Bill, BillLine, Invoice, InvoiceLine, VendorAccount, CustomerAccount
)
from .forms import (
    AccountForm, VendorForm, CustomerForm, ProductForm,
    JournalEntryForm, BillForm, InvoiceForm
)


def to_decimal(value):
    try:
        return Decimal(str(value)) if value and value != '' else Decimal('0')
    except:
        return Decimal('0')


# ---- Dashboard ----

@login_required
def dashboard(request):
    total_accounts = Account.objects.filter(is_active=True).count()
    analysis_accounts = Account.objects.filter(parent__isnull=False).count()
    total_products = Product.objects.filter(is_active=True).count()
    total_vendors = Vendor.objects.filter(is_active=True).count()
    total_customers = Customer.objects.filter(is_active=True).count()
    pending_bills = Bill.objects.filter(status__in=['DRAFT', 'SUBMITTED']).count()
    pending_invoices = Invoice.objects.filter(status__in=['DRAFT', 'SENT']).count()

    return render(request, 'accounting/dashboard.html', {
        'total_accounts': total_accounts,
        'analysis_accounts': analysis_accounts,
        'total_products': total_products,
        'total_vendors': total_vendors,
        'total_customers': total_customers,
        'pending_bills': pending_bills,
        'pending_invoices': pending_invoices,
    })


# ---- Account ----

@login_required
def account_list(request):
    accounts = Account.objects.filter(parent__isnull=True).select_related('parent')
    return render(request, 'accounting/account_list.html', {
        'accounts': accounts,
    })


@login_required
def account_create(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully')
            return redirect('account_list')
    else:
        form = AccountForm()
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Create Account',
    })


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    lines = JournalLine.objects.filter(account=account).select_related('journal_entry').order_by('-journal_entry__date')
    return render(request, 'accounting/account_detail.html', {
        'account': account,
        'lines': lines,
    })


@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account updated')
            return redirect('account_detail', pk=pk)
    else:
        form = AccountForm(instance=account)
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Edit Account',
    })


@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Account deleted')
        return redirect('account_list')
    return render(request, 'accounting/confirm_delete.html', {
        'object': account,
        'type': 'Account',
    })


# ---- Journal Entry ----

@login_required
def journal_entry_list(request):
    entries = JournalEntry.objects.all().order_by('-date', '-id')
    paginator = Paginator(entries, 25)
    page = request.GET.get('page')
    return render(request, 'accounting/journal_entry_list.html', {
        'entries': paginator.get_page(page),
    })


@login_required
def journal_entry_create(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        reference = request.POST.get('reference', '')
        description = request.POST.get('description', '')

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            date = datetime.now().date()

        with transaction.atomic():
            entry = JournalEntry.objects.create(
                date=date,
                reference=reference,
                description=description,
            )

            for i in range(6):
                account_id = request.POST.get(f'account_{i}')
                debit_str = request.POST.get(f'debit_{i}', '0')
                credit_str = request.POST.get(f'credit_{i}', '0')
                debit = to_decimal(debit_str)
                credit = to_decimal(credit_str)

                if account_id and (debit > 0 or credit > 0):
                    JournalLine.objects.create(
                        journal_entry=entry,
                        account_id=account_id,
                        debit=debit,
                        credit=credit,
                    )

            messages.success(request, 'Journal entry created')
            return redirect('journal_entry_detail', pk=entry.id)

    accounts = Account.objects.filter(is_active=True)
    return render(request, 'accounting/journal_entry_form.html', {
        'title': 'Create Journal Entry',
        'accounts': accounts,
    })


@login_required
def journal_entry_detail(request, pk):
    je = get_object_or_404(JournalEntry, pk=pk)
    return render(request, 'accounting/journal_entry_detail.html', {
        'je': je,
    })


@login_required
def journal_entry_post(request, pk):
    je = get_object_or_404(JournalEntry, pk=pk)
    if not je.is_posted:
        je.is_posted = True
        je.posted_at = timezone.now()
        je.save()
        messages.success(request, 'Journal entry posted')
    else:
        messages.warning(request, 'Already posted')
    return redirect('journal_entry_detail', pk=pk)


# ---- Bill ----

@login_required
def bill_list(request):
    bills = Bill.objects.select_related('vendor').all().order_by('-date', '-id')

    status = request.GET.get('status')
    if status:
        bills = bills.filter(status=status)

    paginator = Paginator(bills, 25)
    page = request.GET.get('page')

    return render(request, 'accounting/bill_list.html', {
        'bills': paginator.get_page(page),
        'status': status,
    })


@login_required
def bill_create(request):
    if request.method == 'POST':
        vendor_id = request.POST.get('vendor')
        date_str = request.POST.get('date')
        due_date_str = request.POST.get('due_date')
        reference = request.POST.get('reference', '')
        status = request.POST.get('status', 'DRAFT')
        notes = request.POST.get('notes', '')

        vendor = get_object_or_404(Vendor, pk=vendor_id)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else datetime.now().date()
        except:
            date = datetime.now().date()
            due_date = datetime.now().date()

        with transaction.atomic():
            bill = Bill.objects.create(
                vendor=vendor,
                date=date,
                due_date=due_date,
                reference=reference,
                status=status,
                notes=notes,
            )

            total = Decimal('0')
            for i in range(5):
                product_id = request.POST.get(f'product_{i}')
                description = request.POST.get(f'description_{i}', '')
                qty_str = request.POST.get(f'quantity_{i}', '1')
                price_str = request.POST.get(f'unit_price_{i}', '0')

                quantity = to_decimal(qty_str)
                unit_price = to_decimal(price_str)
                amount = quantity * unit_price

                if amount > 0:
                    BillLine.objects.create(
                        bill=bill,
                        product_id=product_id if product_id else None,
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        amount=amount,
                    )
                    total += amount

            bill.total_amount = total
            bill.save()

        messages.success(request, 'Bill created')
        return redirect('bill_detail', pk=bill.id)

    vendors = Vendor.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    return render(request, 'accounting/bill_form.html', {
        'title': 'Create Bill',
        'vendors': vendors,
        'products': products,
    })


@login_required
def bill_detail(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    return render(request, 'accounting/bill_detail.html', {
        'bill': bill,
    })


@login_required
def bill_edit(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == 'POST':
        vendor_id = request.POST.get('vendor')
        bill.vendor_id = vendor_id
        bill.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
        bill.due_date = datetime.strptime(request.POST.get('due_date'), '%Y-%m-%d').date()
        bill.reference = request.POST.get('reference', '')
        bill.status = request.POST.get('status', 'DRAFT')
        bill.notes = request.POST.get('notes', '')
        bill.save()

        bill.items.all().delete()
        total = Decimal('0')
        for i in range(5):
            product_id = request.POST.get(f'product_{i}')
            description = request.POST.get(f'description_{i}', '')
            qty_str = request.POST.get(f'quantity_{i}', '1')
            price_str = request.POST.get(f'unit_price_{i}', '0')

            quantity = to_decimal(qty_str)
            unit_price = to_decimal(price_str)
            amount = quantity * unit_price

            if amount > 0:
                BillLine.objects.create(
                    bill=bill,
                    product_id=product_id if product_id else None,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount,
                )
                total += amount

        bill.total_amount = total
        bill.save()
        messages.success(request, 'Bill updated')
        return redirect('bill_detail', pk=pk)

    vendors = Vendor.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    return render(request, 'accounting/bill_form.html', {
        'title': 'Edit Bill',
        'vendors': vendors,
        'products': products,
        'bill': bill,
    })


@login_required
def bill_delete(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == 'POST':
        bill.delete()
        messages.success(request, 'Bill deleted')
        return redirect('bill_list')
    return render(request, 'accounting/confirm_delete.html', {
        'object': bill,
        'type': 'Bill',
    })


@login_required
def bill_post(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    if bill.status == 'DRAFT':
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                date=bill.date,
                reference=bill.bill_number,
                description=f"AP Bill {bill.bill_number} from {bill.vendor.name}",
                is_posted=True,
                posted_at=timezone.now(),
            )
            for item in bill.items.all():
                if item.account:
                    JournalLine.objects.create(
                        journal_entry=entry,
                        account=item.account,
                        debit=item.amount,
                        credit=0,
                        description=item.description,
                    )
            JournalLine.objects.create(
                journal_entry=entry,
                account=Account.objects.filter(code='AP').first() or Account.objects.filter(account_type='liability').first(),
                debit=0,
                credit=bill.total_amount,
                description=f"AP - {bill.vendor.name}",
            )
            bill.status = 'SUBMITTED'
            bill.save()
        messages.success(request, 'Bill posted to ledger')
    return redirect('bill_detail', pk=pk)


# ---- Invoice ----

@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('customer').all().order_by('-date', '-id')
    paginator = Paginator(invoices, 25)
    page = request.GET.get('page')
    return render(request, 'accounting/invoice_list.html', {
        'invoices': paginator.get_page(page),
    })


@login_required
def invoice_create(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        date_str = request.POST.get('date')
        due_date_str = request.POST.get('due_date')
        reference = request.POST.get('reference', '')
        status = request.POST.get('status', 'DRAFT')
        notes = request.POST.get('notes', '')

        customer = get_object_or_404(Customer, pk=customer_id)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else datetime.now().date()
        except:
            date = datetime.now().date()
            due_date = datetime.now().date()

        with transaction.atomic():
            invoice = Invoice.objects.create(
                customer=customer,
                date=date,
                due_date=due_date,
                reference=reference,
                status=status,
                notes=notes,
            )

            total = Decimal('0')
            for i in range(5):
                product_id = request.POST.get(f'product_{i}')
                description = request.POST.get(f'description_{i}', '')
                qty_str = request.POST.get(f'quantity_{i}', '1')
                price_str = request.POST.get(f'unit_price_{i}', '0')

                quantity = to_decimal(qty_str)
                unit_price = to_decimal(price_str)
                amount = quantity * unit_price

                if amount > 0:
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        product_id=product_id if product_id else None,
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        amount=amount,
                    )
                    total += amount

            invoice.total_amount = total
            invoice.save()

        messages.success(request, 'Invoice created')
        return redirect('invoice_detail', pk=invoice.id)

    customers = Customer.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    return render(request, 'accounting/invoice_form.html', {
        'title': 'Create Invoice',
        'customers': customers,
        'products': products,
    })


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'accounting/invoice_detail.html', {
        'invoice': invoice,
    })


@login_required
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        invoice.customer_id = customer_id
        invoice.date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
        invoice.due_date = datetime.strptime(request.POST.get('due_date'), '%Y-%m-%d').date()
        invoice.reference = request.POST.get('reference', '')
        invoice.status = request.POST.get('status', 'DRAFT')
        invoice.notes = request.POST.get('notes', '')
        invoice.save()

        invoice.items.all().delete()
        total = Decimal('0')
        for i in range(5):
            product_id = request.POST.get(f'product_{i}')
            description = request.POST.get(f'description_{i}', '')
            qty_str = request.POST.get(f'quantity_{i}', '1')
            price_str = request.POST.get(f'unit_price_{i}', '0')

            quantity = to_decimal(qty_str)
            unit_price = to_decimal(price_str)
            amount = quantity * unit_price

            if amount > 0:
                InvoiceLine.objects.create(
                    invoice=invoice,
                    product_id=product_id if product_id else None,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount,
                )
                total += amount

        invoice.total_amount = total
        invoice.save()
        messages.success(request, 'Invoice updated')
        return redirect('invoice_detail', pk=pk)

    customers = Customer.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    return render(request, 'accounting/invoice_form.html', {
        'title': 'Edit Invoice',
        'customers': customers,
        'products': products,
        'invoice': invoice,
    })


@login_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, 'Invoice deleted')
        return redirect('invoice_list')
    return render(request, 'accounting/confirm_delete.html', {
        'object': invoice,
        'type': 'Invoice',
    })


@login_required
def invoice_post(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status == 'DRAFT':
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                date=invoice.date,
                reference=invoice.invoice_number,
                description=f"AR Invoice {invoice.invoice_number} from {invoice.customer.name}",
                is_posted=True,
                posted_at=timezone.now(),
            )
            JournalLine.objects.create(
                journal_entry=entry,
                account=Account.objects.filter(code='AR').first() or Account.objects.filter(account_type='asset').first(),
                debit=invoice.total_amount,
                credit=0,
                description=f"AR - {invoice.customer.name}",
            )
            for item in invoice.items.all():
                JournalLine.objects.create(
                    journal_entry=entry,
                    account=Account.objects.filter(account_type='income').first(),
                    debit=0,
                    credit=item.amount,
                    description=item.description,
                )
            invoice.status = 'SENT'
            invoice.save()
        messages.success(request, 'Invoice posted to ledger')
    return redirect('invoice_detail', pk=pk)


# ---- Vendor ----

@login_required
def vendor_list(request):
    vendors = Vendor.objects.all().order_by('name')
    query = request.GET.get('q')
    if query:
        vendors = vendors.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    paginator = Paginator(vendors, 25)
    page = request.GET.get('page')
    return render(request, 'accounting/vendor_list.html', {
        'vendors': paginator.get_page(page),
        'q': query,
    })


@login_required
def vendor_create(request):
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendor created')
            return redirect('vendor_list')
    else:
        form = VendorForm()
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Create Vendor',
    })


@login_required
def vendor_edit(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendor updated')
            return redirect('vendor_list')
    else:
        form = VendorForm(instance=vendor)
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Edit Vendor',
    })


@login_required
def vendor_delete(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        vendor.delete()
        messages.success(request, 'Vendor deleted')
        return redirect('vendor_list')
    return render(request, 'accounting/confirm_delete.html', {
        'object': vendor,
        'type': 'Vendor',
    })


@login_required
def vendor_accounts(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    vendor_accounts = VendorAccount.objects.filter(vendor=vendor).select_related('account')
    all_accounts = Account.objects.filter(is_active=True)
    return render(request, 'accounting/vendor_accounts.html', {
        'vendor': vendor,
        'vendor_accounts': vendor_accounts,
        'all_accounts': all_accounts,
    })


@login_required
def add_vendor_account(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        account_id = request.POST.get('account')
        if account_id:
            account = get_object_or_404(Account, pk=account_id)
            VendorAccount.objects.get_or_create(vendor=vendor, account=account)
            messages.success(request, 'Account linked')
    return redirect('vendor_accounts', pk=pk)


@login_required
def unlink_vendor_account(request, pk, account_pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    account = get_object_or_404(Account, pk=account_pk)
    VendorAccount.objects.filter(vendor=vendor, account=account).delete()
    messages.success(request, 'Account unlinked')
    return redirect('vendor_accounts', pk=pk)


# ---- Customer ----

@login_required
def customer_list(request):
    customers = Customer.objects.all().order_by('name')
    query = request.GET.get('q')
    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    paginator = Paginator(customers, 25)
    page = request.GET.get('page')
    return render(request, 'accounting/customer_list.html', {
        'customers': paginator.get_page(page),
        'q': query,
    })


@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer created')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Create Customer',
    })


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Edit Customer',
    })


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted')
        return redirect('customer_list')
    return render(request, 'accounting/confirm_delete.html', {
        'object': customer,
        'type': 'Customer',
    })


@login_required
def customer_accounts(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer_accounts = CustomerAccount.objects.filter(customer=customer).select_related('account')
    all_accounts = Account.objects.filter(is_active=True)
    return render(request, 'accounting/customer_accounts.html', {
        'customer': customer,
        'customer_accounts': customer_accounts,
        'all_accounts': all_accounts,
    })


@login_required
def add_customer_account(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        account_id = request.POST.get('account')
        if account_id:
            account = get_object_or_404(Account, pk=account_id)
            CustomerAccount.objects.get_or_create(customer=customer, account=account)
            messages.success(request, 'Account linked')
    return redirect('customer_accounts', pk=pk)


@login_required
def unlink_customer_account(request, pk, account_pk):
    customer = get_object_or_404(Customer, pk=pk)
    account = get_object_or_404(Account, pk=account_pk)
    CustomerAccount.objects.filter(customer=customer, account=account).delete()
    messages.success(request, 'Account unlinked')
    return redirect('customer_accounts', pk=pk)


# ---- Product ----

@login_required
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('name')
    paginator = Paginator(products, 25)
    page = request.GET.get('page')
    return render(request, 'accounting/product_list.html', {
        'products': paginator.get_page(page),
    })


@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Create Product',
    })


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'accounting/form.html', {
        'form': form,
        'title': 'Edit Product',
    })


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted')
        return redirect('product_list')
    return render(request, 'accounting/confirm_delete.html', {
        'object': product,
        'type': 'Product',
    })


# ---- Reports ----

@login_required
def ledger(request):
    accounts = Account.objects.filter(is_active=True)
    data = []
    for account in accounts:
        debit_total = JournalLine.objects.filter(account=account).aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        credit_total = JournalLine.objects.filter(account=account).aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        if account.account_type in ['asset', 'expense']:
            balance = debit_total - credit_total
        else:
            balance = credit_total - debit_total
        data.append({
            'account': account,
            'debit': debit_total,
            'credit': credit_total,
            'balance': balance,
        })
    return render(request, 'accounting/ledger.html', {
        'data': data,
    })


@login_required
def trial_balance(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    lines = JournalLine.objects.all()
    if start_date:
        lines = lines.filter(journal_entry__date__gte=start_date)
    if end_date:
        lines = lines.filter(journal_entry__date__lte=end_date)

    accounts = Account.objects.filter(is_active=True)
    data = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for account in accounts:
        debit_total = lines.filter(account=account).aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        credit_total = lines.filter(account=account).aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        balance = debit_total - credit_total
        if balance != 0:
            data.append({
                'account': account,
                'balance': balance,
            })
            if balance > 0:
                total_debit += balance
            else:
                total_credit += abs(balance)

    return render(request, 'accounting/trial_balance.html', {
        'data': data,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def balance_sheet(request):
    assets = []
    liabilities = []
    equity = []

    for account in Account.objects.filter(is_active=True):
        balance = account.get_balance()
        if account.account_type == 'asset':
            assets.append({'account': account, 'balance': balance})
        elif account.account_type == 'liability':
            liabilities.append({'account': account, 'balance': balance})
        elif account.account_type == 'equity':
            equity.append({'account': account, 'balance': balance})

    total_assets = sum(item['balance'] for item in assets)
    total_liabilities = sum(item['balance'] for item in liabilities)
    total_equity = sum(item['balance'] for item in equity)

    # Retained earnings = net income
    total_income = sum(
        account.get_balance()
        for account in Account.objects.filter(account_type='income', is_active=True)
    )
    total_expense = sum(
        account.get_balance()
        for account in Account.objects.filter(account_type='expense', is_active=True)
    )
    retained_earnings = total_income - total_expense

    return render(request, 'accounting/balance_sheet.html', {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'retained_earnings': retained_earnings,
    })


@login_required
def income_statement(request):
    revenue_data = []
    expense_data = []

    for account in Account.objects.filter(account_type='income', is_active=True):
        balance = account.get_balance()
        revenue_data.append({'account': account, 'balance': balance})

    for account in Account.objects.filter(account_type='expense', is_active=True):
        balance = account.get_balance()
        expense_data.append({'account': account, 'balance': balance})

    total_revenue = sum(item['balance'] for item in revenue_data)
    total_expense = sum(item['balance'] for item in expense_data)
    net_income = total_revenue - total_expense

    return render(request, 'accounting/income_statement.html', {
        'revenue_data': revenue_data,
        'expense_data': expense_data,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_income': net_income,
    })


@login_required
def analysis_accounts(request):
    accounts = Account.objects.filter(parent__isnull=False).select_related('parent')
    return render(request, 'accounting/analysis_accounts.html', {
        'accounts': accounts,
    })
