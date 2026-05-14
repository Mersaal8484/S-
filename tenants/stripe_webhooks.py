import stripe
import json
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Tenant, Plan, TenantSubscription


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    handlers = {
        'customer.subscription.created': handle_subscription_created,
        'customer.subscription.updated': handle_subscription_updated,
        'customer.subscription.deleted': handle_subscription_deleted,
        'invoice.payment_succeeded': handle_payment_succeeded,
        'invoice.payment_failed': handle_payment_failed,
        'checkout.session.completed': handle_checkout_completed,
    }

    handler = handlers.get(event['type'])
    if handler:
        handler(event['data']['object'])

    return HttpResponse(status=200)


def _get_tenant(subscription):
    return Tenant.objects.filter(stripe_subscription_id=subscription['id']).first()


def _log_subscription(tenant, action, subscription):
    """Log subscription event to TenantSubscription"""
    items = subscription.get('items', {}).get('data', [])
    plan_to = None
    amount = None
    currency = subscription.get('currency', 'SAR')
    if items:
        price = items[0].get('price', {})
        plan_to = Plan.objects.filter(stripe_price_id_monthly=price.get('id')).first()
        amount = price.get('unit_amount')
        if amount:
            amount = Decimal(str(amount)) / 100

    TenantSubscription.objects.create(
        tenant=tenant,
        action=action,
        plan_to=plan_to,
        amount=amount,
        currency=currency.upper(),
        payment_status='succeeded' if action != 'payment_failed' else 'failed',
        stripe_subscription_id=subscription.get('id', ''),
    )


def handle_subscription_created(subscription):
    tenant = _get_tenant(subscription)
    if tenant:
        tenant.subscription_status = 'active'
        tenant.save()
        _log_subscription(tenant, 'created', subscription)


def handle_subscription_updated(subscription):
    tenant = _get_tenant(subscription)
    if tenant:
        status_map = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'trialing': 'trialing',
            'incomplete': 'past_due',
            'incomplete_expired': 'canceled',
        }
        old_status = tenant.subscription_status
        tenant.subscription_status = status_map.get(subscription['status'], 'past_due')
        tenant.is_active = subscription['status'] in ('active', 'trialing')
        tenant.save()

        if subscription['status'] == 'active' and old_status in ('past_due', 'canceled'):
            _log_subscription(tenant, 'renewed', subscription)


def handle_subscription_deleted(subscription):
    tenant = _get_tenant(subscription)
    if tenant:
        tenant.subscription_status = 'canceled'
        tenant.is_active = False
        tenant.save()
        _log_subscription(tenant, 'cancelled', subscription)


def handle_payment_succeeded(invoice):
    if invoice.get('subscription'):
        tenant = Tenant.objects.filter(
            stripe_subscription_id=invoice['subscription']
        ).first()
        if tenant:
            tenant.subscription_status = 'active'
            tenant.save()

            amount = Decimal(str(invoice.get('amount_paid', 0))) / 100
            plan = tenant.plan
            TenantSubscription.objects.create(
                tenant=tenant,
                action='payment',
                plan_to=plan,
                amount=amount,
                currency=invoice.get('currency', 'SAR').upper(),
                payment_status='succeeded',
                stripe_invoice_id=invoice.get('id', ''),
                stripe_subscription_id=invoice.get('subscription', ''),
                notes=f'فاتورة #{invoice.get("number", "")}'
            )


def handle_checkout_completed(session):
    """Handle completed checkout session (for upgrades)"""
    metadata = session.get('metadata', {})
    tenant_id = metadata.get('tenant_id')
    plan_to_id = metadata.get('plan_to')
    plan_from_id = metadata.get('plan_from')

    if tenant_id and plan_to_id:
        tenant = Tenant.objects.filter(id=tenant_id).first()
        plan_to = Plan.objects.filter(id=plan_to_id).first()
        plan_from = Plan.objects.filter(id=plan_from_id).first() if plan_from_id else None

        if tenant and plan_to:
            tenant.plan = plan_to
            tenant.subscription_status = 'active'
            if session.get('subscription'):
                tenant.stripe_subscription_id = session['subscription']
            tenant.save()

            TenantSubscription.objects.create(
                tenant=tenant, action='upgraded',
                plan_from=plan_from, plan_to=plan_to,
                stripe_subscription_id=session.get('subscription', ''),
                notes='ترقية عبر Stripe Checkout'
            )


def handle_payment_failed(invoice):
    if invoice.get('subscription'):
        tenant = Tenant.objects.filter(
            stripe_subscription_id=invoice['subscription']
        ).first()
        if tenant:
            tenant.subscription_status = 'past_due'
            tenant.save()

            TenantSubscription.objects.create(
                tenant=tenant,
                action='payment',
                payment_status='failed',
                stripe_invoice_id=invoice.get('id', ''),
                stripe_subscription_id=invoice.get('subscription', ''),
                notes=f'فشل دفع الفاتورة #{invoice.get("number", "")}'
            )
