import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elem.settings')
django.setup()

from tenants.models import Tenant, Domain

print(f"Current schema: {connection.schema_name}")

print("\nTenants:")
for t in Tenant.objects.all():
    print(f"- {t.schema_name}: {t.company_name}")

print("\nDomains:")
for d in Domain.objects.all():
    print(f"- {d.domain} (Tenant: {d.tenant.schema_name})")
