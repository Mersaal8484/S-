from django.db import models
from decimal import Decimal


class Account(models.Model):
    class AccountType(models.TextChoices):
        ASSET = 'asset', 'Asset'
        LIABILITY = 'liability', 'Liability'
        EQUITY = 'equity', 'Equity'
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_balance(self):
        debit_total = JournalLine.objects.filter(account=self).aggregate(
            total=models.Sum('debit')
        )['total'] or Decimal('0')
        credit_total = JournalLine.objects.filter(account=self).aggregate(
            total=models.Sum('credit')
        )['total'] or Decimal('0')
        if self.account_type in ['asset', 'expense']:
            return debit_total - credit_total
        return credit_total - debit_total


class Vendor(models.Model):
    vendor_code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    tax_id = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.vendor_code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.vendor_code:
            import random
            from datetime import datetime as dt
            self.vendor_code = f"VEN-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)


class Customer(models.Model):
    customer_code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.customer_code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.customer_code:
            import random
            from datetime import datetime as dt
            self.customer_code = f"CUS-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)


class Product(models.Model):
    class ProductType(models.TextChoices):
        PRODUCT = 'product', 'Product'
        SERVICE = 'service', 'Service'

    code = models.CharField(max_length=50, unique=True, blank=True)
    sku = models.CharField(max_length=50, blank=True, default='')
    barcode = models.CharField(max_length=50, blank=True, default='')
    internal_code = models.CharField(max_length=50, blank=True, default='')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.PRODUCT)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            import random
            from datetime import datetime as dt
            self.code = f"PROD-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)


class JournalEntry(models.Model):
    entry_number = models.CharField(max_length=50, unique=True, blank=True)
    date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name_plural = 'Journal entries'

    def __str__(self):
        return f"{self.entry_number} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            import random
            from datetime import datetime as dt
            self.entry_number = f"JE-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def get_total_debit(self):
        return self.lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')

    def get_total_credit(self):
        return self.lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')


class JournalLine(models.Model):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.code}"


class Bill(models.Model):
    class BillStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    bill_number = models.CharField(max_length=50, unique=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='bills')
    date = models.DateField()
    due_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, default='')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=BillStatus.choices, default=BillStatus.DRAFT)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"Bill {self.bill_number}"

    def save(self, *args, **kwargs):
        if not self.bill_number:
            import random
            from datetime import datetime as dt
            self.bill_number = f"BILL-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def get_total(self):
        return self.items.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')


class BillLine(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=200, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.bill.bill_number} - {self.description or self.product.name if self.product else ''}"


class Invoice(models.Model):
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    date = models.DateField()
    due_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True, default='')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import random
            from datetime import datetime as dt
            self.invoice_number = f"INV-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def get_total(self):
        return self.items.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=200, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description or self.product.name if self.product else ''}"


class VendorAccount(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='vendor_accounts')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['vendor', 'account']

    def __str__(self):
        return f"{self.vendor.name} - {self.account.code}"


class CustomerAccount(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_accounts')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['customer', 'account']

    def __str__(self):
        return f"{self.customer.name} - {self.account.code}"
