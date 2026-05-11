from django.core.management.base import BaseCommand
from tenants.models import Plan


class Command(BaseCommand):
    help = 'Seed default SaaS plans'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Basic',
                'tier': 'basic',
                'price_monthly': 49.00,
                'price_yearly': 490.00,
                'max_customers': 1000,
                'max_meters': 5000,
                'max_users': 10,
                'features': {
                    'sms': True,
                    'ewallet': False,
                    'api': False,
                    'field_app': False,
                    'barcode': True,
                },
            },
            {
                'name': 'Professional',
                'tier': 'pro',
                'price_monthly': 149.00,
                'price_yearly': 1490.00,
                'max_customers': 10000,
                'max_meters': 50000,
                'max_users': 50,
                'features': {
                    'sms': True,
                    'ewallet': True,
                    'api': True,
                    'field_app': True,
                    'barcode': True,
                },
            },
            {
                'name': 'Enterprise',
                'tier': 'enterprise',
                'price_monthly': 499.00,
                'price_yearly': 4990.00,
                'max_customers': 999999,
                'max_meters': 999999,
                'max_users': 999,
                'features': {
                    'sms': True,
                    'ewallet': True,
                    'api': True,
                    'field_app': True,
                    'barcode': True,
                },
            },
        ]

        for data in plans_data:
            plan, created = Plan.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Plan '{data['name']}' created"))
            else:
                self.stdout.write(f"Plan '{data['name']}' already exists")
