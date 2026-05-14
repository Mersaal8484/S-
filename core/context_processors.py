from django.db import connection
from django.conf import settings
from django_tenants.utils import get_public_schema_name


def dashboard_stats(request):
    # --- ONE-TIME FIX START ---
    try:
        from tenants.models import Domain
        from django.db import connection
        
        # If any tenant hijacked 127.0.0.1 or localhost, fix it
        # We also check for 'localhost' and empty strings
        problematic = Domain.objects.filter(domain__in=['127.0.0.1', 'localhost', '127.0.0.1:8000', 'localhost:8000'])
        for d in problematic:
            if d.tenant.schema_name != 'public':
                print(f"FIXING DOMAIN HIJACK: {d.domain} was mapped to {d.tenant.schema_name}")
                d.domain = f"{d.tenant.schema_name}.localhost"
                d.save()
    except Exception as e:
        print(f"Domain Fix Error: {e}")
    # --- ONE-TIME FIX END ---

    ctx = {}
    ctx['is_public_schema'] = connection.schema_name == get_public_schema_name()
    print(f"DEBUG: Schema={connection.schema_name} | IsPublic={ctx['is_public_schema']} | Host={request.get_host()}")
    if not ctx['is_public_schema']:
        from django.contrib.auth.models import User
        ctx['user_count'] = User.objects.count()
        ctx['pending_count'] = 0
    try:
        from tenants.models import Tenant, Plan
        ctx['tenant_count'] = Tenant.objects.count()
        ctx['plan_count'] = Plan.objects.count()
    except Exception:
        ctx['tenant_count'] = 0
        ctx['plan_count'] = 0
    return ctx
