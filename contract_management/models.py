from django.db import models


class UoMCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'UoM Category'
        verbose_name_plural = 'UoM Categories'

    def __str__(self):
        return self.name


class UoM(models.Model):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(UoMCategory, on_delete=models.CASCADE, null=True, blank=True)
    factor = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Unit of Measure'
        verbose_name_plural = 'Units of Measure'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'


class Journal(models.Model):
    JOURNAL_TYPE_CHOICES = [
        ('sales', 'Sales'),
        ('purchases', 'Purchases'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('general', 'General'),
    ]

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    journal_type = models.CharField(max_length=50, choices=JOURNAL_TYPE_CHOICES, default='general')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Contract(models.Model):
    METER_TYPE_CHOICES = [
        ('meck', 'Mechanical'),
        ('elec', 'Electronic'),
        ('ppay', 'Prepaid'),
    ]

    METER_PHASE_CHOICES = [
        ('1vas', 'Single Phase'),
        ('3vas', 'Three Phase'),
        ('allvas', 'Transformer'),
    ]

    METER_USAGE_CHOICES = [
        ('home', 'Home'),
        ('trad', 'Commercial'),
        ('gover', 'Government'),
        ('manve', 'Industrial'),
        ('water', 'Water Pump'),
        ('other', 'Other'),
    ]

    RECURRING_RULE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    INVOICING_TYPE_CHOICES = [
        ('pre-paid', 'Pre-paid'),
        ('post-paid', 'Post-paid'),
    ]

    contract_number = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=200)
    partner_old_id = models.CharField(max_length=100, blank=True, null=True)
    partner = models.ForeignKey('billing.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    meter_number = models.CharField(max_length=100, blank=True, null=True)
    meter_type = models.CharField(max_length=20, choices=METER_TYPE_CHOICES, default='meck')
    meter_phase_type = models.CharField(max_length=20, choices=METER_PHASE_CHOICES, default='1vas')
    meter_usage_type = models.CharField(max_length=20, choices=METER_USAGE_CHOICES, default='home')
    meter_first_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    meter_current_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    meter_last_invoice_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    meter_multiplier = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    recurring_invoices = models.BooleanField(default=False)
    recurring_rule_type = models.CharField(max_length=20, choices=RECURRING_RULE_CHOICES, default='monthly')
    recurring_interval = models.IntegerField(default=1)
    recurring_invoicing_type = models.CharField(max_length=20, choices=INVOICING_TYPE_CHOICES, default='post-paid')
    recurring_next_date = models.DateField(null=True, blank=True)
    connection_date = models.DateField(null=True, blank=True)
    contract_date = models.DateField(null=True, blank=True)
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.contract_number or str(self.pk)

    def calculate_used_units(self):
        return self.meter_current_reading - self.meter_last_invoice_reading


class ContractLine(models.Model):
    CONTRACT_TYPE_CHOICES = [
        ('ELECTRIC', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
    ]

    PRICING_TYPE_CHOICES = [
        ('FLAT', 'Fixed Fee'),
        ('PER_UNIT', 'Per Unit'),
        ('TIERED', 'Tiered Pricing'),
    ]

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    uom = models.ForeignKey(UoM, on_delete=models.SET_NULL, null=True, blank=True)
    is_template = models.BooleanField(default=False)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, blank=True, default='')
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='FLAT')
    tier_from = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tier_to = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sequence = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sequence']

    def __str__(self):
        if self.product:
            return f'{self.product.name} - {self.quantity} x {self.unit_price}'
        return self.description or f'Line {self.pk}'

    @property
    def amount(self):
        subtotal = (self.quantity or 0) * (self.unit_price or 0)
        discount_amount = subtotal * (self.discount or 0) / 100
        return subtotal - discount_amount


class MeterReading(models.Model):
    READING_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('invoice', 'Invoice'),
    ]

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='readings')
    reading_date = models.DateTimeField()
    reading_type = models.CharField(max_length=20, choices=READING_TYPE_CHOICES, default='regular')
    previous_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_reading = models.DecimalField(max_digits=12, decimal_places=2)
    is_invoiced = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reading_date']

    def __str__(self):
        return f'{self.contract.name} - {self.reading_date.date()}'

    @property
    def consumption(self):
        return self.current_reading - self.previous_reading

    def save(self, *args, **kwargs):
        if not self.pk:
            self.previous_reading = self.contract.meter_current_reading
        super().save(*args, **kwargs)


class DateRangeType(models.Model):
    name = models.CharField(max_length=100)
    allow_overlap = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Date Range Type'
        verbose_name_plural = 'Date Range Types'

    def __str__(self):
        return self.name


class DateRange(models.Model):
    date_range_type = models.ForeignKey(DateRangeType, on_delete=models.CASCADE, related_name='ranges')
    name = models.CharField(max_length=200)
    date_from = models.DateField()
    date_to = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date_from']

    def __str__(self):
        return f'{self.name} ({self.date_from} - {self.date_to})'


class InvoiceTemplate(models.Model):
    CONTRACT_TYPE_CHOICES = [
        ('ELECTRIC', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
    ]

    PRICING_TYPE_CHOICES = [
        ('FLAT', 'Fixed Fee'),
        ('PER_UNIT', 'Per Unit'),
        ('TIERED', 'Tiered Pricing'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    description = models.CharField(max_length=255, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    uom = models.ForeignKey(UoM, on_delete=models.SET_NULL, null=True, blank=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, blank=True, default='')
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='FLAT')
    is_active = models.BooleanField(default=True)
    tier_from = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tier_to = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Invoice Template'
        verbose_name_plural = 'Invoice Templates'

    def __str__(self):
        if self.product:
            return f'{self.product.name} - {self.unit_price}'
        return f'Template {self.pk}'


class TaskQueue(models.Model):
    TASK_TYPE_CHOICES = [
        ('recurring_invoice', 'Recurring Invoice'),
        ('meter_reading', 'Meter Reading'),
        ('notification', 'Notification'),
        ('report', 'Report Generation'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=200)
    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES, default='recurring_invoice')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=5)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    payload = models.TextField(blank=True, default='{}')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task Queue'
        verbose_name_plural = 'Task Queues'

    def __str__(self):
        return self.name
