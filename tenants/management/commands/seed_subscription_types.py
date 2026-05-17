from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from tenants.models import Tenant


TYPES = [
    {'name_ar': 'سكني', 'name_en': 'Residential'},
    {'name_ar': 'تجاري', 'name_en': 'Commercial'},
    {'name_ar': 'حكومي', 'name_en': 'Government'},
    {'name_ar': 'صناعي', 'name_en': 'Industrial'},
    {'name_ar': 'زراعي', 'name_en': 'Agricultural'},
]


class Command(BaseCommand):
    help = 'Seed default subscription types for all tenants'

    def handle(self, *args, **kwargs):
        from billing.models import SubscriptionType

        schemas = [t.schema_name for t in Tenant.objects.exclude(schema_name='public')]

        for schema in schemas:
            with schema_context(schema):
                count = 0
                for data in TYPES:
                    sub_type, created = SubscriptionType.objects.get_or_create(
                        name_ar=data['name_ar'],
                        defaults=data
                    )
                    if created:
                        count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Schema '{schema}': {count} created, {len(TYPES) - count} existing"
                ))
