from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db import connection
from django_tenants.utils import schema_context
from django.contrib.auth.models import User

from .models import Plan, Tenant, Domain


def landing_page(request):
    """Public landing page"""
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'public/landing.html', {'plans': plans})


def pricing(request):
    """Public pricing page"""
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'public/pricing.html', {'plans': plans})


def register(request):
    """Tenant registration - step 1: choose plan and fill company info"""
    if request.method == 'POST':
        plan_id = request.POST.get('plan')
        plan = get_object_or_404(Plan, pk=plan_id)

        company_name = request.POST.get('company_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        password = request.POST.get('password')

        if not company_name or not email or not password:
            messages.error(request, 'يرجى تعبئة جميع الحقول المطلوبة')
            return redirect('tenants:register')

        schema_name = company_name.lower().replace(' ', '_').replace('-', '_')[:63]

        if Tenant.objects.filter(schema_name=schema_name).exists():
            messages.error(request, 'اسم الشركة مستخدم بالفعل')
            return redirect('tenants:register')

        tenant = Tenant.objects.create(
            company_name=company_name,
            email=email,
            phone=phone,
            plan=plan,
            is_active=True,
        )

        Domain.objects.create(
            domain=f"{schema_name}.{settings.ALLOWED_HOSTS[0] if isinstance(settings.ALLOWED_HOSTS, list) else settings.ALLOWED_HOSTS.split(',')[0] if hasattr(settings.ALLOWED_HOSTS, 'split') else 'yoursaas.com'}",
            tenant=tenant,
            is_primary=True,
        )

        with schema_context(tenant.schema_name):
            User.objects.create_superuser(
                username=email,
                email=email,
                password=password,
            )

        request.session['tenant_id'] = tenant.id
        messages.success(request, f'تم إنشاء الحساب بنجاح! مرحباً {company_name}')
        return redirect('tenants:register_success', tenant_id=tenant.id)

    plans = Plan.objects.filter(is_active=True)
    return render(request, 'public/register.html', {'plans': plans})


def register_success(request, tenant_id):
    """Registration success page with subdomain info"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    domain = tenant.domains.filter(is_primary=True).first()
    return render(request, 'public/register_success.html', {
        'tenant': tenant,
        'domain': domain,
    })
