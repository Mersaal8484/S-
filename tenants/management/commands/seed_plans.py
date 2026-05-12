from django.core.management.base import BaseCommand
from tenants.models import Plan

class Command(BaseCommand):
    help = 'Seed default SaaS plans'

    def handle(self, *args, **kwargs):
        plans = [
            {
                'name': 'Basic',
                'tier': 'basic',
                'price_monthly': 49.00,
                'price_yearly': 490.00,
                'max_customers': 1000,
                'features': {'sms': True, 'api': False}
            },
            {
                'name': 'Pro',
                'tier': 'pro',
                'price_monthly': 149.00,
                'price_yearly': 1490.00,
                'max_customers': 10000,
                'features': {'sms': True, 'api': True, 'ewallet': True}
            },
            {
                'name': 'Enterprise',
                'tier': 'enterprise',
                'price_monthly': 499.00,
                'price_yearly': 4990.00,
                'max_customers': 999999,
                'features': {'sms': True, 'api': True, 'ewallet': True, 'priority_support': True}
            }
        ]

        for plan_data in plans:
            plan, created = Plan.objects.get_or_create(
                tier=plan_data['tier'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Plan {plan.name} already exists'))
