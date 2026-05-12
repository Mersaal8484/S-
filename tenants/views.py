import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.db import IntegrityError, connection
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
        with schema_context('public'):
            plan_id = request.POST.get('plan')
            plan = get_object_or_404(Plan, pk=plan_id)

            company_name = request.POST.get('company_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            password = request.POST.get('password')

            if not company_name or not email or not password:
                messages.error(request, 'يرجى تعبئة جميع الحقول المطلوبة')
                return redirect('tenants:register')

            # Improve schema name generation: handle Arabic by using email prefix if name is non-ASCII
            clean_name = re.sub(r'[^a-z0-9_]', '', company_name.lower().replace(' ', '_').replace('-', '_')).strip('_')
            if not clean_name or len(clean_name) < 2:
                # Use email prefix if company name is all Arabic/special chars
                clean_name = re.sub(r'[^a-z0-9_]', '', email.split('@')[0].lower()).strip('_')
            
            schema_name = clean_name[:63]
            if not schema_name or schema_name[0].isdigit():
                schema_name = 't' + schema_name if schema_name else 'company'

            # Ensure uniqueness
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
                plan=plan,
                is_active=True,
            )

            Domain.objects.create(
                domain=f"{schema_name}.{settings.ALLOWED_HOSTS[0] if isinstance(settings.ALLOWED_HOSTS, list) else settings.ALLOWED_HOSTS.split(',')[0] if hasattr(settings.ALLOWED_HOSTS, 'split') else 'yoursaas.com'}",
                tenant=tenant,
                is_primary=True,
            )

            with schema_context(tenant.schema_name):
                try:
                    User.objects.create_superuser(
                        username=email,
                        email=email,
                        password=password,
                    )
                except IntegrityError:
                    user = User.objects.get(username=email)
                    user.set_password(password)
                    user.is_superuser = True
                    user.is_staff = True
                    user.save()

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
