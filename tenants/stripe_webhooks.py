import stripe
import json
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Tenant


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
    }

    handler = handlers.get(event['type'])
    if handler:
        handler(event['data']['object'])

    return HttpResponse(status=200)


def handle_subscription_created(subscription):
    tenant = Tenant.objects.filter(stripe_subscription_id=subscription['id']).first()
    if tenant:
        tenant.subscription_status = 'active'
        tenant.save()


def handle_subscription_updated(subscription):
    tenant = Tenant.objects.filter(stripe_subscription_id=subscription['id']).first()
    if tenant:
        status_map = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'trialing': 'trialing',
            'incomplete': 'past_due',
            'incomplete_expired': 'canceled',
        }
        tenant.subscription_status = status_map.get(subscription['status'], 'past_due')
        tenant.is_active = subscription['status'] in ('active', 'trialing')
        tenant.save()


def handle_subscription_deleted(subscription):
    tenant = Tenant.objects.filter(stripe_subscription_id=subscription['id']).first()
    if tenant:
        tenant.subscription_status = 'canceled'
        tenant.is_active = False
        tenant.save()


def handle_payment_succeeded(invoice):
    if invoice.get('subscription'):
        tenant = Tenant.objects.filter(
            stripe_subscription_id=invoice['subscription']
        ).first()
        if tenant:
            tenant.subscription_status = 'active'
            tenant.save()


def handle_payment_failed(invoice):
    if invoice.get('subscription'):
        tenant = Tenant.objects.filter(
            stripe_subscription_id=invoice['subscription']
        ).first()
        if tenant:
            tenant.subscription_status = 'past_due'
            tenant.save()
