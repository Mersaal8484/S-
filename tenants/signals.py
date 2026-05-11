from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from .models import Tenant


@receiver(post_save, sender=Tenant)
def create_tenant_schema(sender, instance, created, **kwargs):
    if created:
        with schema_context(instance.schema_name):
            if instance.email:
                User.objects.create_superuser(
                    username=instance.email,
                    email=instance.email,
                    password=instance.company_name.lower().replace(' ', '') + '123',
                )
