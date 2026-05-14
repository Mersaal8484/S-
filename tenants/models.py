from django.db import models
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
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
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
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
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
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'اشتراك'
        verbose_name_plural = 'سجل الاشتراكات'

    def __str__(self):
        return f"{self.tenant.company_name} - {self.get_action_display()} - {self.created_at.date()}"
