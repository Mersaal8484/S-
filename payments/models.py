from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class PaymentGateway(models.Model):
    """بوابات الدفع المحلية والعالمية"""
    
    GATEWAY_TYPES = [
        ('fawry', 'Fawry'),
        ('paymob', 'Paymob'),
        ('vodafone_cash', 'Vodafone Cash'),
        ('bank_transfer', 'تحويل بنكي'),
        ('cash', 'نقدي'),
        ('credit_card', 'بطاقة ائتمان'),
    ]
    
    name = models.CharField('اسم البوابة', max_length=100)
    gateway_type = models.CharField('نوع البوابة', max_length=50, choices=GATEWAY_TYPES)
    is_active = models.BooleanField('مفعل', default=True)
    
    # API Credentials (encrypted in production)
    api_key = models.CharField('API Key', max_length=500, blank=True)
    api_secret = models.CharField('API Secret', max_length=500, blank=True)
    merchant_id = models.CharField('Merchant ID', max_length=200, blank=True)
    
    # Configuration
    config_json = models.JSONField('إعدادات إضافية', default=dict, blank=True)
    
    # Fees
    fixed_fee = models.DecimalField('رسوم ثابتة', max_digits=10, decimal_places=2, default=0)
    percentage_fee = models.DecimalField('نسبة الرسوم %', max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_gateways'
        verbose_name = 'بوابة دفع'
        verbose_name_plural = 'بوابات الدفع'
    
    def __str__(self):
        return f"{self.name} ({self.get_gateway_type_display()})"


class SubscriptionPayment(models.Model):
    """مدفوعات الاشتراكات الشهرية/السنوية"""
    
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('processing', 'جاري المعالجة'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('refunded', 'مسترد'),
        ('cancelled', 'ملغي'),
    ]
    
    # Relations
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payments')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Payment Details
    amount = models.DecimalField('المبلغ', max_digits=10, decimal_places=2)
    currency = models.CharField('العملة', max_length=3, default='EGP')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Transaction Info
    transaction_id = models.CharField('رقم المعاملة', max_length=200, unique=True)
    gateway_transaction_id = models.CharField('رقم المعاملة بالبوابة', max_length=200, blank=True)
    
    # Billing Period
    billing_period_start = models.DateField('بداية الفترة')
    billing_period_end = models.DateField('نهاية الفترة')
    
    # Payment Method Details
    payment_method = models.CharField('طريقة الدفع', max_length=100, blank=True)
    payment_proof = models.FileField('إثبات الدفع', upload_to='payment_proofs/', blank=True, null=True)
    
    # Metadata
    notes = models.TextField('ملاحظات', blank=True)
    metadata = models.JSONField('بيانات إضافية', default=dict, blank=True)
    
    # Timestamps
    paid_at = models.DateTimeField('تاريخ الدفع', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_payments'
        verbose_name = 'دفعة اشتراك'
        verbose_name_plural = 'دفعات الاشتراكات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant.company_name} - {self.amount} {self.currency} - {self.get_status_display()}"
    
    def mark_as_paid(self):
        """تحديد الدفعة كمدفوعة"""
        self.status = 'completed'
        self.paid_at = timezone.now()
        self.save()


class Invoice(models.Model):
    """فواتير الاشتراكات"""
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('sent', 'مرسلة'),
        ('paid', 'مدفوعة'),
        ('overdue', 'متأخرة'),
        ('cancelled', 'ملغاة'),
    ]
    
    # Relations
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='invoices')
    payment = models.OneToOneField(SubscriptionPayment, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice')
    
    # Invoice Details
    invoice_number = models.CharField('رقم الفاتورة', max_length=50, unique=True)
    issue_date = models.DateField('تاريخ الإصدار', default=timezone.now)
    due_date = models.DateField('تاريخ الاستحقاق')
    
    # Amounts
    subtotal = models.DecimalField('المبلغ الفرعي', max_digits=10, decimal_places=2)
  tax_amount = models.DecimalField('الضريبة', max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField('الخصم', max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField('المبلغ الإجمالي', max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Metadata
    notes = models.TextField('ملاحظات', blank=True)
    
    # Timestamps
    sent_at = models.DateTimeField('تاريخ الإرسال', null=True, blank=True)
    paid_at = models.DateTimeField('تاريخ السداد', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_invoices'
        verbose_name = 'فاتورة اشتراك'
        verbose_name_plural = 'فواتير الاشتراكات'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['invoice_number']),
        ]
    
    def __str__(self):
        return f"فاتورة {self.invoice_number} - {self.tenant.company_name}"
