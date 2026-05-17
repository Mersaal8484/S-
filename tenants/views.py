import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db import connection
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Tenant, Domain
from django.db.models import Count, Avg, Q, F
from datetime import timedelta
import json
from django.contrib.admin.views.decorators import staff_member_required

def landing_page(request):
    """Public landing page"""
    return render(request, 'public/landing.html')


def pricing(request):
    """Public pricing page"""
    return render(request, 'public/pricing.html')


def register(request):
    """Tenant registration"""
    if request.method == 'POST':
        with schema_context('public'):
            company_name = request.POST.get('company_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            password = request.POST.get('password')

            if not company_name or not email or not password:
                messages.error(request, 'يرجى تعبئة جميع الحقول المطلوبة')
                return redirect('tenants:register')

            clean_name = re.sub(r'[^a-z0-9_]', '', company_name.lower().replace(' ', '_').replace('-', '_')).strip('_')
            if not clean_name or len(clean_name) < 2:
                clean_name = re.sub(r'[^a-z0-9_]', '', email.split('@')[0].lower()).strip('_')

            schema_name = clean_name[:63]
            if not schema_name or schema_name[0].isdigit():
                schema_name = 't' + schema_name if schema_name else 'company'

            base_schema = schema_name
            counter = 1
            while Tenant.objects.filter(schema_name=schema_name).exists():
                schema_name = f"{base_schema[:60]}_{counter}"
                counter += 1

            tenant = Tenant.objects.create(
                schema_name=schema_name,
                company_name=company_name,
                email=email,
                phone=phone,
                is_active=True,
            )

            Domain.objects.create(
                domain=f"{schema_name}.{settings.ALLOWED_HOSTS[0] if isinstance(settings.ALLOWED_HOSTS, list) else settings.ALLOWED_HOSTS.split(',')[0] if hasattr(settings.ALLOWED_HOSTS, 'split') else 'yoursaas.com'}",
                tenant=tenant,
                is_primary=True,
            )

            # User was created by Tenant.save() -> _bootstrap_tenant in public schema
            user = User.objects.get(username=email)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()

            request.session['tenant_id'] = tenant.id
            messages.success(request, f'تم إنشاء الحساب بنجاح! مرحباً {company_name}')
            return redirect('tenants:register_success', tenant_id=tenant.id)

    return render(request, 'public/register.html')


def register_success(request, tenant_id):
    """Registration success page with subdomain info"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    domain = tenant.domains.filter(is_primary=True).first()
    return render(request, 'public/register_success.html', {
        'tenant': tenant,
        'domain': domain,
    })


@staff_member_required
def tenant_dashboard(request):
    active_page = 'settings' if request.path.startswith('/admin/settings/') else request.GET.get('page', 'overview')

    from billing.models import SystemSettings, SubscriptionType, InvoiceLineTemplate

    settings_obj = SystemSettings.objects.first()
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()

    subscription_types = list(SubscriptionType.objects.all())
    templates_by_type = {}
    for st in subscription_types:
        templates = InvoiceLineTemplate.objects.filter(type=st)
        templates_by_type[st.id] = {
            'type': {
                'id': st.id,
                'name_ar': st.name_ar,
                'name_en': st.name_en,
                'is_active': st.is_active,
                'description': st.description,
                'code': getattr(st, 'code', None),
            },
            'templates': list(templates.values(
                'id', 'line_order', 'line_name_ar', 'line_name_en',
                'calculation_type', 'is_taxable'
            ))
        }

    context = {
        'active_page': active_page,
        'settings': settings_obj,
        'subscription_types': subscription_types,
        'templates_by_type_json': json.dumps(templates_by_type),
    }

    return render(request, 'admin/index_tenant.html', context)


def super_admin_dashboard(request):
    """Super Admin Dashboard with Advanced Live Statistics"""
    if not request.user.is_staff:
        messages.error(request, 'غير مصرح لك بالوصول')
        return redirect('/')

    total_tenants = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()
    inactive_tenants = total_tenants - active_tenants

    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_tenants_30d = Tenant.objects.filter(created_at__gte=thirty_days_ago).count()

    monthly_growth = []
    for i in range(11, -1, -1):
        start = timezone.now() - timedelta(days=30*i)
        end = start + timedelta(days=30)
        count = Tenant.objects.filter(created_at__gte=start, created_at__lt=end).count()
        monthly_growth.append({
            'month': start.strftime('%b'),
            'count': count
        })

    with connection.cursor() as cursor:
        cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast')")
        existing_schemas = {row[0] for row in cursor.fetchall()}

    recent_tenants = Tenant.objects.order_by('-created_on')[:10]
    for t in recent_tenants:
        t.schema_status = 'موجود' if t.schema_name in existing_schemas else 'مفقود'

    churned_tenants = Tenant.objects.filter(
        is_active=False,
        updated_at__gte=thirty_days_ago
    ).count() if hasattr(Tenant, 'updated_at') else 0
    churn_rate = (churned_tenants / total_tenants * 100) if total_tenants > 0 else 0

    context = {
        'total_tenants': total_tenants,
        'active_tenants': active_tenants,
        'inactive_tenants': inactive_tenants,
        'new_tenants_30d': new_tenants_30d,
        'monthly_growth': monthly_growth,
        'recent_tenants': recent_tenants,
        'churn_rate': round(churn_rate, 2),
    }

    return render(request, 'admin/super_admin_dashboard.html', context)
