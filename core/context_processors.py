from django.db import connection
from django.conf import settings


def dashboard_stats(request):
    ctx = {}
    if hasattr(request, 'tenant') and request.tenant:
        schema = connection.schema_name
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
