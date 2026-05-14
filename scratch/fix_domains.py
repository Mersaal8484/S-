import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elem.settings')
django.setup()

from tenants.models import Tenant, Domain
from django.db import connection

print(f"Current schema: {connection.schema_name}")

# List all domains
domains = Domain.objects.all()
print("Current domains:")
for d in domains:
    print(f"- Domain: {d.domain}, Tenant: {d.tenant.schema_name}, Primary: {d.is_primary}")

# Identify if any tenant has 127.0.0.1 or localhost as domain
problematic_domains = Domain.objects.filter(domain__in=['127.0.0.1', 'localhost', 'localhost:8000', '127.0.0.1:8000'])
for d in problematic_domains:
    if d.tenant.schema_name != 'public':
        print(f"Found problematic domain: {d.domain} assigned to tenant {d.tenant.schema_name}")
        # Rename it to something else or delete it
        old_domain = d.domain
        d.domain = f"fixed_{d.tenant.schema_name}.localhost"
        d.save()
        print(f"Fixed: {old_domain} -> {d.domain}")

# Ensure public schema has a domain if needed
# (django-tenants usually doesn't need one for public if SHOW_PUBLIC_IF_NO_TENANT_FOUND is True,
# but having one helps)
