from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from tenants.models import Tenant
from integrations.models import Integration


class Command(BaseCommand):
    help = 'Seed default integration providers for all tenants'

    def handle(self, *args, **kwargs):
        providers = [
            {'name': 'Stripe', 'provider_code': 'stripe', 'category': 'PAYMENT',
             'description': 'Payment processing platform for online businesses',
             'documentation_url': 'https://stripe.com/docs'},
            {'name': 'PayPal', 'provider_code': 'paypal', 'category': 'PAYMENT',
             'description': 'Online payment system for global commerce',
             'documentation_url': 'https://developer.paypal.com/docs'},
            {'name': 'Mada', 'provider_code': 'mada', 'category': 'PAYMENT',
             'description': 'Saudi Arabian national payment card system',
             'documentation_url': 'https://www.mada.com.sa'},
            {'name': 'STC Pay', 'provider_code': 'stcpay', 'category': 'PAYMENT',
             'description': 'Saudi digital wallet and payment service',
             'documentation_url': 'https://stcpay.com.sa'},
            {'name': 'Tap', 'provider_code': 'tap', 'category': 'PAYMENT',
             'description': 'Regional payment gateway for MENA region',
             'documentation_url': 'https://tap.company'},
            {'name': 'Twilio', 'provider_code': 'twilio', 'category': 'COMMUNICATION',
             'description': 'Cloud communications platform for SMS and voice',
             'documentation_url': 'https://www.twilio.com/docs'},
            {'name': 'SendGrid', 'provider_code': 'sendgrid', 'category': 'COMMUNICATION',
             'description': 'Email delivery and marketing platform',
             'documentation_url': 'https://docs.sendgrid.com'},
            {'name': 'WhatsApp Cloud API', 'provider_code': 'whatsapp', 'category': 'COMMUNICATION',
             'description': 'Meta official WhatsApp Business messaging API',
             'documentation_url': 'https://developers.facebook.com/docs/whatsapp'},
            {'name': 'Firebase Cloud Messaging', 'provider_code': 'fcm', 'category': 'COMMUNICATION',
             'description': 'Cross-platform push notification service',
             'documentation_url': 'https://firebase.google.com/docs/cloud-messaging'},
            {'name': 'HubSpot', 'provider_code': 'hubspot', 'category': 'CRM',
             'description': 'CRM platform for marketing, sales, and service',
             'documentation_url': 'https://developers.hubspot.com'},
            {'name': 'Salesforce', 'provider_code': 'salesforce', 'category': 'CRM',
             'description': 'Enterprise CRM and sales management platform',
             'documentation_url': 'https://developer.salesforce.com/docs'},
            {'name': 'Zoho Books', 'provider_code': 'zohobooks', 'category': 'ACCOUNTING',
             'description': 'Online accounting and bookkeeping software',
             'documentation_url': 'https://www.zoho.com/books/api'},
            {'name': 'QuickBooks', 'provider_code': 'quickbooks', 'category': 'ACCOUNTING',
             'description': 'Small business accounting and finance platform',
             'documentation_url': 'https://developer.intuit.com/app/developer/qbo'},
            {'name': 'Google Maps', 'provider_code': 'google_maps', 'category': 'OTHER',
             'description': 'Geocoding, directions, and location services',
             'documentation_url': 'https://developers.google.com/maps'},
            {'name': 'OpenWeatherMap', 'provider_code': 'openweather', 'category': 'OTHER',
             'description': 'Weather data and forecast API',
             'documentation_url': 'https://openweathermap.org/api'},
            {'name': 'AWS S3', 'provider_code': 'aws_s3', 'category': 'OTHER',
             'description': 'Scalable cloud object storage service',
             'documentation_url': 'https://docs.aws.amazon.com/s3'},
        ]

        schemas = [t.schema_name for t in Tenant.objects.all()]

        for schema in schemas:
            with schema_context(schema):
                count = 0
                for data in providers:
                    integration, created = Integration.objects.get_or_create(
                        provider_code=data['provider_code'],
                        defaults=data
                    )
                    if created:
                        count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Schema '{schema}': {count} created, {len(providers) - count} existing"
                ))
