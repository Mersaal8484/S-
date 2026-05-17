import logging
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django_tenants.utils import schema_context
from django.contrib.auth.models import User

logger = logging.getLogger('tenants')


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
    """Company/Organization in the SaaS system."""
    auto_create_schema = False

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

    def save(self, verbosity=0, *args, **kwargs):
        is_new = self.pk is None

        if is_new:
            # Step 1: Persist the model row to obtain a primary key
            # (required by create_schema). This sends post_save, so any
            # connected handler must tolerate a missing schema.
            super().save(*args, **kwargs)

            # Step 2: Create the PostgreSQL schema and run tenant migrations
            self.create_schema(
                check_if_exists=True,
                verbosity=max(verbosity, 0),
            )

            # Step 3: Bootstrap initial data inside the new tenant schema
            try:
                self._bootstrap_tenant()
            except Exception:
                logger.exception(
                    "Bootstrap failed for tenant %s (schema %s)",
                    self.company_name, self.schema_name,
                )
        else:
            super().save(*args, **kwargs)

    def _bootstrap_tenant(self):
        """Create the initial superuser and seed default data inside this tenant's schema."""
        if not self.email:
            return

        with schema_context(self.schema_name):
            password = f"{self.company_name.lower().replace(' ', '')}123"
            User.objects.create_superuser(
                username=self.email,
                email=self.email,
                password=password,
            )
            logger.info(
                "Superuser %s created in schema %s",
                self.email, self.schema_name,
            )

            self._seed_subscription_types()

    def _seed_subscription_types(self):
        """Seed default subscription types for this tenant."""
        from billing.models import SubscriptionType
        types = [
            {'name_ar': 'سكني', 'name_en': 'Residential'},
            {'name_ar': 'تجاري', 'name_en': 'Commercial'},
            {'name_ar': 'حكومي', 'name_en': 'Government'},
            {'name_ar': 'صناعي', 'name_en': 'Industrial'},
            {'name_ar': 'زراعي', 'name_en': 'Agricultural'},
        ]
        for data in types:
            SubscriptionType.objects.get_or_create(name_ar=data['name_ar'], defaults=data)
        logger.info("Default subscription types seeded in schema %s", self.schema_name)

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
