from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime as dt


class SubscriptionType(models.Model):
    name_ar = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Subscription Type'
        verbose_name_plural = 'Subscription Types'

    def __str__(self):
        return self.name_ar


class Customer(models.Model):
    customer_number = models.CharField(max_length=50, unique=True, blank=True, default='')
    full_name_ar = models.CharField(max_length=150)
    full_name_en = models.CharField(max_length=150, blank=True, default='')
    national_id = models.CharField(max_length=50, blank=True, default='')
    mobile_phone = models.CharField(max_length=20, blank=True, default='')
    phone2 = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    registration_date = models.DateField(auto_now_add=True)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.customer_number:
            import random
            from datetime import datetime
            self.customer_number = f"CUST-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_number} - {self.full_name_ar}"


class Contract(models.Model):
    class ContractStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        TERMINATED = 'terminated', 'Terminated'
        EXPIRED = 'expired', 'Expired'

    contract_number = models.CharField(max_length=50, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contracts')
    type = models.ForeignKey(SubscriptionType, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    contract_status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.ACTIVE)
    connection_load = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Connection Load (kW)')
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.contract_number:
            import random
            from datetime import datetime
            self.contract_number = f"CTR-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        if not self.start_date:
            self.start_date = dt.now().date()
        super().save(*args, **kwargs)
        return f"{self.contract_number} - {self.customer.full_name_ar}"


class Meter(models.Model):
    class MeterStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        DEFECTIVE = 'defective', 'Defective'
        REPLACED = 'replaced', 'Replaced'
        REMOVED = 'removed', 'Removed'

    class MeterType(models.TextChoices):
        ANALOG = 'analog', 'Analog'
        DIGITAL = 'digital', 'Digital'
        PREPAID = 'prepaid', 'Prepaid'

    meter_number = models.CharField(max_length=50, unique=True, blank=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='meters')
    meter_model = models.CharField(max_length=100, blank=True, default='')
    meter_type = models.CharField(max_length=20, choices=MeterType.choices, default=MeterType.ANALOG)
    initial_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_approved_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    last_reading_date = models.DateField(null=True, blank=True)
    meter_status = models.CharField(max_length=20, choices=MeterStatus.choices, default=MeterStatus.ACTIVE)
    location_description = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-installation_date']

    def save(self, *args, **kwargs):
        if not self.meter_number:
            import random
            from datetime import datetime
            self.meter_number = f"M-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        if not self.installation_date:
            self.installation_date = dt.now().date()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.meter_number} - {self.contract.contract_number}"


class InvoiceLineTemplate(models.Model):
    class CalculationType(models.TextChoices):
        FIXED = 'fixed', 'Fixed'
        PERCENTAGE = 'percentage', 'Percentage'
        TIERED_KWH = 'tiered_kwh', 'Tiered kWh'
        SINGLE_RATE_KWH = 'single_rate_kwh', 'Single Rate kWh'
        DEMAND_CHARGE = 'demand_charge', 'Demand Charge'
        MINIMUM_CHARGE = 'minimum_charge', 'Minimum Charge'

    type = models.ForeignKey(SubscriptionType, on_delete=models.CASCADE, related_name='line_templates')
    line_order = models.IntegerField()
    line_name_ar = models.CharField(max_length=150)
    line_name_en = models.CharField(max_length=150, blank=True)
    calculation_type = models.CharField(max_length=20, choices=CalculationType.choices)
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    percentage_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    depends_on = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_taxable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['type', 'line_order']
        unique_together = ['type', 'line_order']

    def __str__(self):
        return f"{self.type.name_ar} - {self.line_name_ar}"


class InvoiceLineFormulaDetail(models.Model):
    template = models.ForeignKey(InvoiceLineTemplate, on_delete=models.CASCADE, related_name='formula_details')
    min_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate_or_amount = models.DecimalField(max_digits=12, decimal_places=4)
    is_rate_per_kwh = models.BooleanField(default=False)

    class Meta:
        ordering = ['template', 'min_value']

    def __str__(self):
        return f"{self.template.line_name_ar} - {self.rate_or_amount}"


class BillingPeriod(models.Model):
    class BillingStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        READING_OPEN = 'reading_open', 'Reading Open'
        READING_CLOSED = 'reading_closed', 'Reading Closed'
        BILLING_IN_PROGRESS = 'billing_in_progress', 'Billing In Progress'
        BILLING_COMPLETED = 'billing_completed', 'Billing Completed'
        CLOSED = 'closed', 'Closed'

    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        BI_MONTHLY = 'bi_monthly', 'Bi-Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        CUSTOM = 'custom', 'Custom'

    period_name = models.CharField(max_length=100)
    period_code = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    reading_start_date = models.DateField()
    reading_end_date = models.DateField()
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    status = models.CharField(max_length=30, choices=BillingStatus.choices, default=BillingStatus.DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_periods')
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.period_name} ({self.period_code})"


class MeterReadingSubmission(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        FLAGGED_REVIEW = 'flagged_review', 'Flagged for Review'

    class ReadingSource(models.TextChoices):
        MANUAL_ENTRY = 'manual_entry', 'Manual Entry'
        MOBILE_APP = 'mobile_app', 'Mobile App'
        SMS = 'sms', 'SMS'
        SMART_METER = 'smart_meter', 'Smart Meter'
        ESTIMATED = 'estimated', 'Estimated'

    period = models.ForeignKey(BillingPeriod, on_delete=models.CASCADE, related_name='readings', null=True, blank=True)
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name='reading_submissions')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    previous_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    submitted_reading = models.DecimalField(max_digits=12, decimal_places=2)
    reading_date = models.DateField(null=True, blank=True)
    reading_source = models.CharField(max_length=20, choices=ReadingSource.choices, default=ReadingSource.MANUAL_ENTRY)
    reader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_readings')
    reader_notes = models.TextField(blank=True)
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    approved_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    final_consumption = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reading_date:
            from datetime import datetime as dt
            self.reading_date = dt.now().date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.meter.meter_number} - {self.reading_date}"
    
    @property
    def consumption(self):
        if self.final_consumption is not None:
            return self.final_consumption
        if self.approved_reading:
            return self.approved_reading - self.previous_reading
        return self.submitted_reading - self.previous_reading


class MeterReading(models.Model):
    class ReadingSource(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        SMART_METER = 'smart_meter', 'Smart Meter'
        ESTIMATED = 'estimated', 'Estimated'

    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name='readings')
    reading_date = models.DateField(null=True, blank=True)
    previous_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_reading = models.DecimalField(max_digits=12, decimal_places=2)
    reading_source = models.CharField(max_length=20, choices=ReadingSource.choices, default=ReadingSource.MANUAL)
    reader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='meter_readings')
    notes = models.TextField(blank=True)
    is_billed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['meter', 'reading_date']
        ordering = ['-reading_date']

    def save(self, *args, **kwargs):
        if not self.reading_date:
            from datetime import datetime as dt
            self.reading_date = dt.now().date()
        super().save(*args, **kwargs)

    @property
    def consumption(self):
        return self.current_reading - self.previous_reading

    def __str__(self):
        return f"{self.meter.meter_number} - {self.reading_date}"


class Invoice(models.Model):
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ISSUED = 'issued', 'Issued'
        PAID = 'paid', 'Paid'
        PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    invoice_number = models.CharField(max_length=50, unique=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='invoices')
    subscription_type = models.ForeignKey('SubscriptionType', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    reading = models.ForeignKey(MeterReading, on_delete=models.SET_NULL, null=True, blank=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    previous_indebtedness = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    period = models.ForeignKey(BillingPeriod, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return self.invoice_number

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def final_amount(self):
        return self.total_amount + self.previous_indebtedness

    @property
    def remaining_with_debt(self):
        return self.final_amount - self.paid_amount


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    template = models.ForeignKey(InvoiceLineTemplate, on_delete=models.CASCADE)
    line_name_ar = models.CharField(max_length=150)
    line_name_en = models.CharField(max_length=150, blank=True)
    calculation_basis = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    line_order = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['line_order']

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.line_name_ar}"
    
    @property
    def subtotal(self):
        return self.quantity * self.rate


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CARD = 'card', 'Card'
        ONLINE = 'online', 'Online'
        CHEQUE = 'cheque', 'Cheque'

    class PaymentSource(models.TextChoices):
        CASH = 'cash', 'Cash'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CARD = 'card', 'Card'
        ONLINE = 'online', 'Online'
        CHEQUE = 'cheque', 'Cheque'
        COLLECTOR = 'collector', 'Collector'
        EWALLET = 'ewallet', 'E-Wallet'

    payment_number = models.CharField(max_length=50, unique=True, blank=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    source_type = models.CharField(max_length=20, choices=PaymentSource.choices, default=PaymentSource.CASH)
    reference_number = models.CharField(max_length=100, blank=True, default='')
    cheque_number = models.CharField(max_length=50, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    period = models.ForeignKey(BillingPeriod, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')

    class Meta:
        ordering = ['-payment_date']

    def save(self, *args, **kwargs):
        if not self.payment_number:
            import random
            from datetime import datetime
            self.payment_number = f"PAY-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        if not self.payment_method:
            self.payment_method = 'cash'
        try:
            if self.contract_id and not self.customer_id:
                self.customer = self.contract.customer
            if self.contract_id and not self.invoice_id:
                self.invoice = self.contract.invoices.filter(invoice_status__in=['issued', 'partially_paid']).first()
        except:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payment_number} - {self.amount}"


class Penalty(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='penalties')
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2)
    penalty_days = models.IntegerField()
    calculated_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.penalty_amount}"


class CustomerBalance(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='balance')
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.customer_number} - {self.current_balance}"


class BalanceLedger(models.Model):
    class TransactionType(models.TextChoices):
        INVOICE_CREATED = 'invoice_created', 'Invoice Created'
        PAYMENT_RECEIVED = 'payment_received', 'Payment Received'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        REFUND = 'refund', 'Refund'
        PENALTY = 'penalty', 'Penalty'
        WRITE_OFF = 'write_off', 'Write Off'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    reference_id = models.IntegerField(null=True, blank=True)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.customer.customer_number} - {self.transaction_type}"


class FinancialAdjustment(models.Model):
    class AdjustmentType(models.TextChoices):
        DEBIT = 'debit', 'Debit'
        CREDIT = 'credit', 'Credit'

    adjustment_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='adjustments')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    adjustment_type = models.CharField(max_length=10, choices=AdjustmentType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_adjustments')
    approval_date = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.adjustment_number} - {self.amount}"


class MeterChangeLog(models.Model):
    class ChangeReason(models.TextChoices):
        DEFECTIVE = 'defective', 'Defective'
        UPGRADE = 'upgrade', 'Upgrade'
        DOWNGRADE = 'downgrade', 'Downgrade'
        DAMAGED = 'damaged', 'Damaged'
        THEFT = 'theft', 'Theft'
        OTHER = 'other', 'Other'

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='meter_changes')
    old_meter = models.ForeignKey(Meter, on_delete=models.SET_NULL, null=True, blank=True, related_name='old_changes')
    new_meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name='new_changes')
    old_meter_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_meter_initial_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    change_reason = models.CharField(max_length=20, choices=ChangeReason.choices)
    change_date = models.DateField()
    authorized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.contract.contract_number} - {self.change_reason}"


class BillingQueue(models.Model):
    class QueueStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        RETRY = 'retry', 'Retry'

    period = models.ForeignKey(BillingPeriod, on_delete=models.CASCADE, related_name='queue_items')
    submission = models.ForeignKey(MeterReadingSubmission, on_delete=models.CASCADE, related_name='queue_items')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    queue_status = models.CharField(max_length=20, choices=QueueStatus.choices, default=QueueStatus.PENDING)
    priority = models.IntegerField(default=5)
    retry_count = models.IntegerField(default=0)
    max_retry = models.IntegerField(default=3)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'created_at']

    def __str__(self):
        return f"{self.contract.contract_number} - {self.queue_status}"


class BillingProcessLog(models.Model):
    period = models.ForeignKey(BillingPeriod, on_delete=models.CASCADE, related_name='process_logs')
    queue = models.ForeignKey(BillingQueue, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    affected_records = models.IntegerField(default=0)
    processed_by = models.CharField(max_length=100, default='system')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.status}"


class SMSProvider(models.Model):
    provider_name = models.CharField(max_length=100)
    api_url = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255, blank=True)
    sender_name = models.CharField(max_length=50)
    country_code = models.CharField(max_length=10, default='966')
    is_active = models.BooleanField(default=False)
    priority = models.IntegerField(default=1)
    cost_per_sms = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.provider_name


class SMSTemplate(models.Model):
    class TemplateType(models.TextChoices):
        INVOICE_CREATED = 'InvoiceCreated', 'Invoice Created'
        PAYMENT_RECEIVED = 'PaymentReceived', 'Payment Received'
        BILL_DUE_SOON = 'BillDueSoon', 'Bill Due Soon'
        BILL_OVERDUE = 'BillOverdue', 'Bill Overdue'
        METER_READING_REMINDER = 'MeterReadingReminder', 'Meter Reading Reminder'
        CONTRACT_EXPIRY_ALERT = 'ContractExpiryAlert', 'Contract Expiry Alert'
        WELCOME_MESSAGE = 'WelcomeMessage', 'Welcome Message'
        PAYMENT_REMINDER = 'PaymentReminder', 'Payment Reminder'
        READING_APPROVED = 'ReadingApproved', 'Reading Approved'
        READING_REJECTED = 'ReadingRejected', 'Reading Rejected'
        CUSTOM = 'Custom', 'Custom'

    template_type = models.CharField(max_length=30, choices=TemplateType.choices)
    title_ar = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    content_template_ar = models.TextField()
    content_template_en = models.TextField(blank=True)
    variables_allowed = models.TextField(blank=True)
    language = models.CharField(max_length=2, default='ar')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title_ar or self.template_type


class SMSQueue(models.Model):
    class SMSStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        RETRYING = 'retrying', 'Retrying'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sms_queue')
    mobile_number = models.CharField(max_length=20)
    template = models.ForeignKey(SMSTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    message_content = models.TextField()
    status = models.CharField(max_length=20, choices=SMSStatus.choices, default=SMSStatus.PENDING)
    retry_count = models.IntegerField(default=0)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider = models.ForeignKey(SMSProvider, on_delete=models.SET_NULL, null=True, blank=True)
    cost = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.mobile_number} - {self.status}"


class SMSLog(models.Model):
    sms = models.ForeignKey(SMSQueue, on_delete=models.CASCADE, related_name='logs')
    provider_response_code = models.CharField(max_length=50, blank=True)
    provider_response_message = models.TextField(blank=True)
    delivery_status = models.CharField(max_length=50, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.sms.id} - {self.delivery_status}"


class SystemSettings(models.Model):
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField(blank=True)
    setting_description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.setting_key

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'


class Collector(models.Model):
    class CollectorStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        TERMINATED = 'terminated', 'Terminated'

    collector_code = models.CharField(max_length=50, unique=True)
    full_name_ar = models.CharField(max_length=150)
    full_name_en = models.CharField(max_length=150, blank=True)
    national_id = models.CharField(max_length=50, unique=True, blank=True)
    mobile_phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    hire_date = models.DateField()
    collector_status = models.CharField(max_length=20, choices=CollectorStatus.choices, default=CollectorStatus.ACTIVE)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.collector_code} - {self.full_name_ar}"


class CollectorCashbox(models.Model):
    class CashboxStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'
        SUSPENDED = 'suspended', 'Suspended'

    collector = models.ForeignKey(Collector, on_delete=models.CASCADE, related_name='cashboxes')
    cashbox_name = models.CharField(max_length=100)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=CashboxStatus.choices, default=CashboxStatus.ACTIVE)
    opened_date = models.DateTimeField(auto_now_add=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cashbox_name} - {self.current_balance}"


class CollectorCashboxTransaction(models.Model):
    class TransactionType(models.TextChoices):
        COLLECTION = 'collection', 'Collection'
        DEPOSIT_TO_COMPANY = 'deposit_to_company', 'Deposit to Company'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        OPENING_BALANCE = 'opening_balance', 'Opening Balance'
        CLOSING_BALANCE = 'closing_balance', 'Closing Balance'

    cashbox = models.ForeignKey(CollectorCashbox, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"


class CashDeposit(models.Model):
    class DepositStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        UNDER_REVIEW = 'under_review', 'Under Review'

    class DepositMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CASH_AT_HQ = 'cash_at_hq', 'Cash at HQ'
        CHEQUE = 'cheque', 'Cheque'
        ONLINE = 'online', 'Online'

    deposit_number = models.CharField(max_length=50, unique=True)
    collector = models.ForeignKey(Collector, on_delete=models.CASCADE, related_name='deposits')
    cashbox = models.ForeignKey(CollectorCashbox, on_delete=models.CASCADE)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_date = models.DateField()
    deposit_time = models.TimeField()
    deposit_method = models.CharField(max_length=20, choices=DepositMethod.choices)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=DepositStatus.choices, default=DepositStatus.PENDING)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_deposits')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.deposit_number} - {self.deposit_amount}"


class EWalletProvider(models.Model):
    provider_name = models.CharField(max_length=100)
    provider_code = models.CharField(max_length=50, unique=True)
    api_url = models.CharField(max_length=255, blank=True)
    api_key = models.CharField(max_length=255, blank=True)
    merchant_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    transaction_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    settlement_days = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.provider_name


class CustomerEWallet(models.Model):
    class EWalletStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        CLOSED = 'closed', 'Closed'

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ewallets')
    provider = models.ForeignKey(EWalletProvider, on_delete=models.CASCADE)
    wallet_number = models.CharField(max_length=100)
    wallet_owner_name = models.CharField(max_length=150, blank=True)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=EWalletStatus.choices, default=EWalletStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['customer', 'provider', 'wallet_number']

    def __str__(self):
        return f"{self.customer.customer_number} - {self.provider.provider_name}"


class EWalletTransaction(models.Model):
    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        CANCELLED = 'cancelled', 'Cancelled'

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='ewallet_transactions')
    ewallet = models.ForeignKey(CustomerEWallet, on_delete=models.CASCADE)
    transaction_reference = models.CharField(max_length=100, unique=True)
    transaction_amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    provider_response = models.TextField(blank=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    settlement_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    @property
    def net_amount(self):
        return self.transaction_amount - self.transaction_fee

    def __str__(self):
        return f"{self.transaction_reference} - {self.transaction_amount}"


class MeterReader(models.Model):
    class ReaderStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        TERMINATED = 'terminated', 'Terminated'

    reader_code = models.CharField(max_length=50, unique=True)
    full_name_ar = models.CharField(max_length=150)
    full_name_en = models.CharField(max_length=150, blank=True)
    national_id = models.CharField(max_length=50, unique=True, blank=True)
    mobile_phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    hire_date = models.DateField()
    region = models.CharField(max_length=100, blank=True)
    max_readings_per_day = models.IntegerField(default=100)
    reader_status = models.CharField(max_length=20, choices=ReaderStatus.choices, default=ReaderStatus.ACTIVE)
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reader_code} - {self.full_name_ar}"


class Route(models.Model):
    class RouteType(models.TextChoices):
        METER_READING = 'meter_reading', 'Meter Reading'
        COLLECTION = 'collection', 'Collection'
        BOTH = 'both', 'Both'

    route_code = models.CharField(max_length=50, unique=True, blank=True)
    route_name_ar = models.CharField(max_length=150)
    route_name_en = models.CharField(max_length=150, blank=True)
    route_type = models.CharField(max_length=20, choices=RouteType.choices)
    region = models.CharField(max_length=100, blank=True)
    area_description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.route_code:
            import random
            self.route_code = f"R-{dt.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.route_code} - {self.route_name_ar}"


class RouteContract(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='contracts')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='route_assigned')
    stop_order = models.IntegerField()
    priority = models.IntegerField(default=5)
    estimated_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estimated_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['route', 'contract']
        ordering = ['route', 'stop_order']

    def __str__(self):
        return f"{self.route.route_code} - {self.stop_order}"


class RouteAssignment(models.Model):
    class AssignmentStatus(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Shift(models.TextChoices):
        MORNING = 'morning', 'Morning'
        EVENING = 'evening', 'Evening'
        FULL_DAY = 'full_day', 'Full Day'

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='assignments')
    assigned_to_type = models.CharField(max_length=20)
    assigned_to_id = models.IntegerField()
    assignment_date = models.DateField()
    shift = models.CharField(max_length=20, choices=Shift.choices, default=Shift.FULL_DAY)
    status = models.CharField(max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.PLANNED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.route.route_code} - {self.assignment_date}"


class RouteExecution(models.Model):
    class ExecutionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DONE = 'done', 'Done'
        SKIPPED = 'skipped', 'Skipped'

    assignment = models.ForeignKey(RouteAssignment, on_delete=models.CASCADE, related_name='executions')
    route_contract = models.ForeignKey(RouteContract, on_delete=models.CASCADE)
    stop_order = models.IntegerField()
    actual_reading = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reading_submission = models.ForeignKey(MeterReadingSubmission, on_delete=models.SET_NULL, null=True, blank=True)
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    execution_status = models.CharField(max_length=20, choices=ExecutionStatus.choices, default=ExecutionStatus.PENDING)
    skip_reason = models.TextField(blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.stop_order} - {self.execution_status}"


class RouteTrackingLog(models.Model):
    class ActionType(models.TextChoices):
        START = 'start', 'Start'
        COMPLETE = 'complete', 'Complete'
        DONE_CONTRACT = 'done_contract', 'Done Contract'
        SKIP_CONTRACT = 'skip_contract', 'Skip Contract'

    assignment = models.ForeignKey(RouteAssignment, on_delete=models.CASCADE, related_name='tracking_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    route_contract = models.ForeignKey(RouteContract, on_delete=models.SET_NULL, null=True, blank=True)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} - {self.created_at}"