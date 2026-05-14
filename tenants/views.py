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


def upgrade_checkout(request, tenant_id):
    """Create Stripe Checkout Session for plan upgrade"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    plan_id = request.GET.get('plan')
    plan = get_object_or_404(Plan, pk=plan_id)

    if plan.tier == tenant.plan.tier:
        messages.info(request, 'أنت بالفعل مشترك في هذه الخطة')
        return redirect('tenants:register_success', tenant_id=tenant.id)

    billing_cycle = request.GET.get('cycle', 'monthly')
    price_field = 'stripe_price_id_monthly' if billing_cycle == 'monthly' else 'stripe_price_id_yearly'
    stripe_price_id = getattr(plan, price_field, '')

    if not stripe_price_id or not settings.STRIPE_SECRET_KEY:
        # Direct admin upgrade (no Stripe configured)
        old_plan = tenant.plan
        tenant.plan = plan
        tenant.save()
        from .models import TenantSubscription
        TenantSubscription.objects.create(
            tenant=tenant, action='upgraded',
            plan_from=old_plan, plan_to=plan,
            notes='ترقية بدون Stripe'
        )
        messages.success(request, f'تم ترقية حسابك إلى {plan.name}')
        return redirect('tenants:register_success', tenant_id=tenant.id)

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if not tenant.stripe_customer_id:
            customer = stripe.Customer.create(
                email=tenant.email,
                name=tenant.company_name,
                metadata={'tenant_id': tenant.id}
            )
            tenant.stripe_customer_id = customer.id
            tenant.save()

        session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            mode='subscription',
            line_items=[{'price': stripe_price_id, 'quantity': 1}],
            metadata={
                'tenant_id': tenant.id,
                'plan_from': str(tenant.plan.id) if tenant.plan else '',
                'plan_to': str(plan.id),
            },
            success_url=request.build_absolute_uri(
                reverse('tenants:upgrade_success', args=[tenant.id])
            ),
            cancel_url=request.build_absolute_uri(
                reverse('tenants:register_success', args=[tenant.id])
            ),
        )
        return redirect(session.url)
    except Exception as e:
        messages.error(request, f'فشل إنشاء جلسة الدفع: {e}')
        return redirect('tenants:register_success', tenant_id=tenant.id)


def upgrade_success(request, tenant_id):
    """Upgrade completed successfully"""
    tenant = get_object_or_404(Tenant, pk=tenant_id)
    messages.success(request, 'تمت الترقية بنجاح ✅')
    return redirect('tenants:register_success', tenant_id=tenant.id)
