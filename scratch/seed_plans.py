import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elem.settings')
django.setup()

from tenants.models import Plan, Tenant, Domain

plans = Plan.objects.all()
if not plans.exists():
    print("No plans found. Seeding default plans...")
    Plan.objects.create(
        name='Basic',
        tier='basic',
        price_monthly=49.00,
        price_yearly=490.00,
        max_customers=1000
    )
    Plan.objects.create(
        name='Pro',
        tier='pro',
        price_monthly=149.00,
        price_yearly=1490.00,
        max_customers=10000
    )
    print("Plans seeded.")
else:
    for p in plans:
        print(f"Plan: {p.name} (${p.price_monthly})")

tenants = Tenant.objects.all()
print(f"Tenants count: {tenants.count()}")
for t in tenants:
    print(f"- {t.schema_name}: {t.company_name}")
