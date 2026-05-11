from django.urls import path
from . import stripe_webhooks

urlpatterns = [
    path('', stripe_webhooks.stripe_webhook, name='stripe-webhook'),
]
