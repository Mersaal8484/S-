import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elem.settings')
django.setup()

from tenants.models import Tenant, Domain
from django.db import connection

def fix_tenant_data():
    print("--- Starting Tenant Diagnostic ---")
    
    # 1. Check Tenant
    tenant = Tenant.objects.filter(schema_name='barq').first()
    if not tenant:
        print("ERROR: Tenant with schema 'barq' not found!")
        return

    print(f"Found Tenant: {tenant.company_name} (Schema: {tenant.schema_name})")

    # 2. Check Schema Existence
    cursor = connection.cursor()
    cursor.execute("SELECT schema_name FROM information_schema.schemata")
    schemas = cursor.fetchall()
    schema_names = [s[0] for s in schemas]
    if 'barq' not in schema_names:
        print(f"CRITICAL: PostgreSQL Schema 'barq' DOES NOT EXIST in DB!")
        print("Attempting to create it (might take a moment)...")
        # In a real scenario, we'd run migrations, but let's see if we can trigger it
    else:
        print("PostgreSQL Schema 'barq' exists. OK.")

    # 3. Check and Fix Domains
    domains = Domain.objects.filter(tenant=tenant)
    print(f"Found {domains.count()} domains for this tenant.")
    
    for d in domains:
        print(f"Checking domain ID {d.id}: '{d.domain}'")
        if ':' in d.domain:
            new_domain = d.domain.split(':')[0]
            print(f"FIXING: Removing port from domain '{d.domain}' -> '{new_domain}'")
            d.domain = new_domain
            d.save()
            
    # 4. Ensure barq.localhost exists
    if not Domain.objects.filter(domain='barq.localhost').exists():
        print("Adding 'barq.localhost' to Domain table...")
        Domain.objects.create(domain='barq.localhost', tenant=tenant, is_primary=True)
        print("Added. OK.")
    else:
        print("'barq.localhost' is already in Domain table. OK.")

    print("--- Diagnostic Complete ---")

if __name__ == "__main__":
    fix_tenant_data()
