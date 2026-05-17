from django.db import models
from django.utils import timezone
from django_tenants.models import TenantMixin, DomainMixin


class Plan(models.Model):
    """SaaS Subscription Plans"""
    class PlanTier(models.TextChoices):
        BASIC = 'basic', 'Basic'           # Up to 1000 customers
        PRO = 'pro', 'Pro'                 # Up to 10,000 customers
        ENTERPRISE = 'enterprise', 'Enterprise'  # Unlimited

    name = models.CharField(max_length=50)
    tier = models.CharField(max_length=20, choices=PlanTier.choices, default=PlanTier.BASIC)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    max_customers = models.IntegerField(default=1000)
    max_meters = models.IntegerField(default=5000)
    max_users = models.IntegerField(default=10)
    features = models.JSONField(default=dict)  # {'sms': True, 'ewallet': True, 'api': True}
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.price_monthly}/month"


class Tenant(TenantMixin):
    """Company/Organization in the SaaS system"""
    company_name = models.CharField(max_length=200)
    company_name_ar = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=2, default='SA')  # ISO 3166
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('trialing', 'Trial'),
            ('active', 'Active'),
            ('past_due', 'Past Due'),
            ('canceled', 'Canceled'),
        ],
        default='trialing'
    )
    trial_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    # django-tenants setting: automatically create schema on save
    auto_create_schema = True

    def __str__(self):
        return self.company_name


class Domain(DomainMixin):
    """Subdomain for each tenant: company.yoursaas.com"""
    pass


class TenantSubscription(models.Model):
    """Track subscription changes and payments for each tenant"""
    class SubscriptionAction(models.TextChoices):
        CREATED = 'created', 'اشتراك جديد'
        UPGRADED = 'upgraded', 'ترقية'
        DOWNGRADED = 'downgraded', 'تخفيض'
        RENEWED = 'renewed', 'تجديد'
        CANCELLED = 'cancelled', 'إلغاء'
        PAYMENT = 'payment', 'دفعة'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'قيد الانتظار'
        SUCCEEDED = 'succeeded', 'ناجحة'
        FAILED = 'failed', 'فاشلة'
        REFUNDED = 'refunded', 'مستردة'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='subscriptions')
    action = models.CharField(max_length=20, choices=SubscriptionAction.choices)
    plan_from = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions_from')
    plan_to = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions_to')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='SAR')
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.SUCCEEDED)
    payment_gateway = models.CharField(max_length=50, blank=True, help_text='بوابة الدفع المستخدمة')
    transaction_id = models.CharField(max_length=200, blank=True, help_text='رقم العملية من بوابة الدفع')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'اشتراك'
        verbose_name_plural = 'سجل الاشتراكات'

    def __str__(self):
        return f"{self.tenant.company_name} - {self.get_action_display()} - {self.created_at.date()}"


class PlatformSettings(models.Model):
    """إعدادات المنصة العامة - يُخزَّن سجل واحد فقط (Singleton)"""

    # ── معلومات المنصة ──────────────────────────────────────────────────
    platform_name = models.CharField(max_length=200, default='S-B SaaS', verbose_name='اسم المنصة')
    platform_name_ar = models.CharField(max_length=200, default='منصة S-B', verbose_name='اسم المنصة (عربي)')
    support_email = models.EmailField(blank=True, verbose_name='بريد الدعم')
    support_phone = models.CharField(max_length=30, blank=True, verbose_name='هاتف الدعم')
    platform_url = models.URLField(blank=True, verbose_name='رابط المنصة')

    # ── إعدادات Stripe / الفوترة SaaS ────────────────────────────────────
    stripe_publishable_key = models.CharField(max_length=300, blank=True, verbose_name='مفتاح Stripe العام')
    stripe_secret_key = models.CharField(max_length=300, blank=True, verbose_name='مفتاح Stripe السري')
    stripe_webhook_secret = models.CharField(max_length=300, blank=True, verbose_name='سر Stripe Webhook')
    stripe_mode = models.CharField(
        max_length=10,
        choices=[('test', 'اختبار'), ('live', 'إنتاج')],
        default='test',
        verbose_name='وضع Stripe'
    )

    # ── إعدادات Webhook عامة ─────────────────────────────────────────────
    webhook_secret_global = models.CharField(max_length=300, blank=True, verbose_name='سر Webhook العام')
    webhook_url_payment = models.URLField(blank=True, verbose_name='Webhook الدفعات')
    webhook_url_subscription = models.URLField(blank=True, verbose_name='Webhook الاشتراكات')
    webhook_retry_attempts = models.PositiveSmallIntegerField(default=3, verbose_name='عدد محاولات إعادة الإرسال')
    webhook_timeout_seconds = models.PositiveSmallIntegerField(default=30, verbose_name='مهلة الانتظار (ثانية)')

    # ── إعدادات REST API ──────────────────────────────────────────────────
    api_rate_limit_per_minute = models.PositiveIntegerField(default=60, verbose_name='حد الطلبات/دقيقة')
    api_max_page_size = models.PositiveIntegerField(default=100, verbose_name='أقصى حجم صفحة')
    api_jwt_expiry_minutes = models.PositiveIntegerField(default=60, verbose_name='انتهاء JWT (دقيقة)')
    api_allow_cors = models.BooleanField(default=True, verbose_name='السماح بـ CORS')
    api_cors_origins = models.TextField(blank=True, help_text='نطاق في كل سطر', verbose_name='نطاقات CORS المسموحة')
    api_documentation_enabled = models.BooleanField(default=True, verbose_name='تفعيل وثائق API')

    # ── إعدادات المحاسبة ─────────────────────────────────────────────────
    default_currency = models.CharField(max_length=3, default='SAR', verbose_name='العملة الافتراضية')
    default_vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15.00, verbose_name='نسبة الضريبة الافتراضية %')
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1, verbose_name='شهر بداية السنة المالية')
    enable_double_entry = models.BooleanField(default=True, verbose_name='تفعيل القيد المزدوج')
    auto_create_journal_entries = models.BooleanField(default=True, verbose_name='إنشاء قيود محاسبية تلقائياً')
    invoice_prefix = models.CharField(max_length=10, default='INV', verbose_name='بادئة رقم الفاتورة')
    invoice_auto_number = models.BooleanField(default=True, verbose_name='ترقيم الفواتير تلقائياً')
    invoice_due_days = models.PositiveSmallIntegerField(default=30, verbose_name='أيام الاستحقاق الافتراضية')

    # ── إعدادات السداد / الأقساط ─────────────────────────────────────────
    payment_grace_days = models.PositiveSmallIntegerField(default=7, verbose_name='أيام السماح قبل التأخير')
    late_payment_penalty_pct = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, verbose_name='نسبة غرامة التأخير %')
    allow_installments = models.BooleanField(default=True, verbose_name='السماح بالأقساط')
    max_installment_months = models.PositiveSmallIntegerField(default=12, verbose_name='أقصى عدد أشهر للتقسيط')
    installment_min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100.00, verbose_name='أقل مبلغ للتقسيط')
    allow_partial_payment = models.BooleanField(default=True, verbose_name='السماح بالدفع الجزئي')
    allow_advance_payment = models.BooleanField(default=True, verbose_name='السماح بالدفع المسبق')

    # ── إعدادات المحافظ الإلكترونية ──────────────────────────────────────
    ewallet_enabled = models.BooleanField(default=False, verbose_name='تفعيل المحافظ الإلكترونية')
    ewallet_providers = models.JSONField(
        default=dict,
        verbose_name='مزودو المحافظ',
        help_text='{"stcpay": {"enabled": true, "merchant_id": "", "api_key": ""}}'
    )
    stcpay_enabled = models.BooleanField(default=False, verbose_name='STC Pay')
    stcpay_merchant_id = models.CharField(max_length=200, blank=True, verbose_name='STC Pay Merchant ID')
    stcpay_api_key = models.CharField(max_length=300, blank=True, verbose_name='STC Pay API Key')
    stcpay_webhook_secret = models.CharField(max_length=300, blank=True, verbose_name='STC Pay Webhook Secret')

    mada_enabled = models.BooleanField(default=False, verbose_name='مدى')
    mada_merchant_id = models.CharField(max_length=200, blank=True, verbose_name='Mada Merchant ID')
    mada_api_key = models.CharField(max_length=300, blank=True, verbose_name='Mada API Key')

    tabby_enabled = models.BooleanField(default=False, verbose_name='Tabby (تابي)')
    tabby_api_key = models.CharField(max_length=300, blank=True, verbose_name='Tabby Public Key')
    tabby_secret_key = models.CharField(max_length=300, blank=True, verbose_name='Tabby Secret Key')

    tamara_enabled = models.BooleanField(default=False, verbose_name='Tamara (تمارا)')
    tamara_api_key = models.CharField(max_length=300, blank=True, verbose_name='Tamara Token')
    tamara_webhook_secret = models.CharField(max_length=300, blank=True, verbose_name='Tamara Webhook Secret')

    # ── إعدادات المستأجرين والنطاقات ─────────────────────────────────────
    default_trial_days = models.PositiveSmallIntegerField(default=14, verbose_name='أيام التجربة الافتراضية')
    auto_activate_on_payment = models.BooleanField(default=True, verbose_name='تفعيل تلقائي عند الدفع')
    require_domain_verification = models.BooleanField(default=False, verbose_name='التحقق من النطاق')
    allowed_custom_domains = models.BooleanField(default=True, verbose_name='السماح بنطاقات مخصصة')
    max_domains_per_tenant = models.PositiveSmallIntegerField(default=5, verbose_name='أقصى نطاقات للمستأجر')
    auto_send_welcome_email = models.BooleanField(default=True, verbose_name='إرسال بريد ترحيب تلقائياً')
    tenant_schema_prefix = models.CharField(max_length=10, default='t_', blank=True, verbose_name='بادئة Schema')

    # ── إعدادات الإشعارات ─────────────────────────────────────────────────
    sms_provider = models.CharField(
        max_length=30,
        choices=[('', 'غير محدد'), ('twilio', 'Twilio'), ('unifonic', 'Unifonic'), ('msegat', 'Msegat'), ('zain', 'Zain SMS')],
        blank=True, default='',
        verbose_name='مزود SMS'
    )
    sms_api_key = models.CharField(max_length=300, blank=True, verbose_name='SMS API Key')
    sms_sender_id = models.CharField(max_length=50, blank=True, verbose_name='معرف المرسل SMS')
    email_backend = models.CharField(max_length=100, blank=True, default='django.core.mail.backends.smtp.EmailBackend', verbose_name='مزود البريد')
    email_host = models.CharField(max_length=200, blank=True, verbose_name='SMTP Host')
    email_port = models.PositiveSmallIntegerField(default=587, verbose_name='SMTP Port')
    email_use_tls = models.BooleanField(default=True, verbose_name='TLS')
    email_host_user = models.CharField(max_length=200, blank=True, verbose_name='SMTP Username')
    email_host_password = models.CharField(max_length=300, blank=True, verbose_name='SMTP Password')
    default_from_email = models.EmailField(blank=True, verbose_name='بريد المرسل الافتراضي')

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=150, blank=True, verbose_name='آخر تعديل بواسطة')

    class Meta:
        verbose_name = 'إعدادات المنصة'
        verbose_name_plural = 'إعدادات المنصة'

    def __str__(self):
        return f'إعدادات {self.platform_name}'

    @classmethod
    def get_settings(cls):
        """Always return the single settings instance (Singleton pattern)"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
