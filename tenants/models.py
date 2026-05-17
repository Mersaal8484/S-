import logging
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django_tenants.utils import schema_context
from django.contrib.auth.models import User

logger = logging.getLogger('tenants')


class Tenant(TenantMixin):
    """Company/Organization in the SaaS system."""
    auto_create_schema = False

    company_name = models.CharField(max_length=200)
    company_name_ar = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=2, default='YE')  # ISO 3166
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
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
        """Create the initial superuser and seed default data."""
        if not self.email:
            return

        with schema_context('public'):
            password = f"{self.company_name.lower().replace(' ', '')}123"
            user, created = User.objects.get_or_create(
                username=self.email,
                defaults={'email': self.email}
            )
            if created:
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.save()
            
            TenantUser.objects.get_or_create(
                user=user,
                defaults={'tenant': self, 'is_tenant_admin': True}
            )
            
            logger.info(
                "Superuser %s created/linked in public schema for %s",
                self.email, self.schema_name,
            )

        with schema_context(self.schema_name):
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

class TenantUser(models.Model):
    """Links a shared User to a specific Tenant."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant_profile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    is_tenant_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.tenant.company_name if self.tenant else 'System'}"



class Domain(DomainMixin):
    """Subdomain for each tenant: company.yoursaas.com"""
    pass


