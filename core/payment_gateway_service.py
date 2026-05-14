from abc import ABC, abstractmethod
from decimal import Decimal
import requests

from integrations.models import IntegrationConfig


class PaymentGateway(ABC):
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.credentials = config.credentials or {}
        self.base_url = config.base_url.rstrip('/') if config.base_url else ''

    @abstractmethod
    def initiate(self, invoice, amount: Decimal, ref: str) -> dict:
        pass

    @abstractmethod
    def verify(self, transaction_id: str = None, payload: dict = None) -> dict:
        pass


class FawryGateway(PaymentGateway):
    def initiate(self, invoice, amount: Decimal, ref: str) -> dict:
        merchant_code = self.credentials.get('merchant_code')
        security_key = self.credentials.get('security_key')
        if not merchant_code or not security_key:
            raise ValueError('Fawry configuration is incomplete: merchant_code/security_key required')

        customer = invoice.contract.customer
        payload = {
            'merchantCode': merchant_code,
            'merchantRefNumber': ref,
            'customer': {
                'name': customer.full_name_ar or getattr(customer, 'full_name_en', '') or customer.email,
                'mobile': getattr(customer, 'mobile_phone', '')[:20],
                'email': getattr(customer, 'email', ''),
            },
            'paymentMethod': {'type': 'PAYATFAWRY'},
            'order': {
                'description': f'Invoice {invoice.invoice_number}',
                'amount': float(amount),
                'currency': self.credentials.get('currency', 'EGP'),
            }
        }

        url = f"{self.base_url}/ECommerceWeb/Fawry/payments/initialize"
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()

        redirect_url = (
            data.get('paymentUrl')
            or data.get('paymentURL')
            or data.get('resources', {}).get('paymentURL', '')
            or data.get('redirectUrl', '')
        )

        return {
            'status': 'pending',
            'transaction_id': data.get('merchantRefNumber') or data.get('paymentReference') or ref,
            'redirect_url': redirect_url,
            'raw_response': data,
        }

    def verify(self, transaction_id: str = None, payload: dict = None) -> dict:
        if payload:
            status = payload.get('orderStatus') or payload.get('status')
            amount = payload.get('orderAmount') or payload.get('amount')
            paid = str(status).upper() in ('PAID', 'SUCCESS', 'COMPLETED')
            return {
                'status': 'paid' if paid else 'pending',
                'amount': Decimal(str(amount or 0)),
                'transaction_id': transaction_id or payload.get('merchantRefNumber'),
                'payload': payload,
            }

        if not transaction_id:
            raise ValueError('transaction_id required for Fawry verification')

        merchant_code = self.credentials.get('merchant_code')
        url = f"{self.base_url}/ECommerceWeb/Fawry/payments/PaymentInquiry"
        response = requests.post(url, json={
            'merchantCode': merchant_code,
            'merchantRefNumber': transaction_id,
        }, timeout=15)
        response.raise_for_status()
        data = response.json()
        status = data.get('orderStatus') or data.get('status')
        amount = data.get('orderAmount') or data.get('amount')
        paid = str(status).upper() in ('PAID', 'SUCCESS', 'COMPLETED')
        return {
            'status': 'paid' if paid else 'pending',
            'amount': Decimal(str(amount or 0)),
            'transaction_id': transaction_id,
            'payload': data,
        }


class PaymobGateway(PaymentGateway):
    def initiate(self, invoice, amount: Decimal, ref: str) -> dict:
        api_key = self.credentials.get('api_key')
        integration_id = self.credentials.get('integration_id')
        iframe_id = self.credentials.get('iframe_id')
        if not api_key or not integration_id or not iframe_id:
            raise ValueError('Paymob configuration is incomplete: api_key/integration_id/iframe_id required')

        auth_token = self._get_auth_token(api_key)
        order_id = self._create_order(auth_token, invoice, amount, ref)
        payment_token = self._request_payment_key(auth_token, invoice, amount, order_id, integration_id)

        redirect_url = f"https://accept.paymob.com/api/acceptance/iframes/{iframe_id}?payment_token={payment_token}"
        return {
            'status': 'pending',
            'transaction_id': order_id,
            'redirect_url': redirect_url,
        }

    def _get_auth_token(self, api_key: str) -> str:
        url = f"{self.base_url}/api/auth/tokens"
        response = requests.post(url, json={'api_key': api_key}, timeout=15)
        response.raise_for_status()
        data = response.json()
        token = data.get('token')
        if not token:
            raise ValueError('Paymob auth failed: token not returned')
        return token

    def _create_order(self, auth_token: str, invoice, amount: Decimal, ref: str) -> str:
        url = f"{self.base_url}/api/ecommerce/orders"
        payload = {
            'auth_token': auth_token,
            'delivery_needed': False,
            'amount_cents': int(amount * 100),
            'currency': self.credentials.get('currency', 'EGP'),
            'merchant_order_id': ref,
            'items': [],
        }
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        order_id = str(data.get('id') or data.get('order', {}).get('id'))
        if not order_id:
            raise ValueError('Paymob order creation failed')
        return order_id

    def _request_payment_key(self, auth_token: str, invoice, amount: Decimal, order_id: str, integration_id: str) -> str:
        url = f"{self.base_url}/api/acceptance/payment_keys"
        customer = invoice.contract.customer
        billing_data = {
            'first_name': customer.full_name_ar or getattr(customer, 'full_name_en', '') or '',
            'last_name': '',
            'email': getattr(customer, 'email', ''),
            'phone_number': getattr(customer, 'mobile_phone', ''),
            'street': '',
            'building': '',
            'floor': '',
            'apartment': '',
            'city': getattr(customer, 'city', ''),
            'state': getattr(customer, 'country', ''),
            'country': getattr(customer, 'country', ''),
            'postal_code': '',
        }
        payload = {
            'auth_token': auth_token,
            'amount_cents': int(amount * 100),
            'expiration': 3600,
            'order_id': order_id,
            'billing_data': billing_data,
            'currency': self.credentials.get('currency', 'EGP'),
            'integration_id': integration_id,
        }
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        token = data.get('token')
        if not token:
            raise ValueError('Paymob payment key request failed')
        return token

    def verify(self, transaction_id: str = None, payload: dict = None) -> dict:
        if payload:
            success = payload.get('success')
            amount = payload.get('amount_cents') or payload.get('amount')
            paid = success in (True, 'true', 'True', '1', 1)
            amount_value = Decimal(str(amount or 0))
            if payload.get('amount_cents'):
                amount_value = amount_value / Decimal('100')
            return {
                'status': 'paid' if paid else 'pending',
                'amount': amount_value,
                'transaction_id': transaction_id or payload.get('id'),
                'payload': payload,
            }

        if not transaction_id:
            raise ValueError('transaction_id required for Paymob verification')

        api_key = self.credentials.get('api_key')
        auth_token = self._get_auth_token(api_key)
        url = f"{self.base_url}/api/acceptance/transactions/{transaction_id}?token={auth_token}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        paid = data.get('success') in (True, 'true', 'True', '1', 1)
        amount = data.get('amount_cents') or data.get('amount')
        amount_value = Decimal(str(amount or 0))
        if data.get('amount_cents'):
            amount_value = amount_value / Decimal('100')
        return {
            'status': 'paid' if paid else 'pending',
            'amount': amount_value,
            'transaction_id': transaction_id,
            'payload': data,
        }


GATEWAY_MAP = {
    'fawry': FawryGateway,
    'paymob': PaymobGateway,
}


def get_gateway(config: IntegrationConfig) -> PaymentGateway:
    if not config or not config.integration:
        raise ValueError('A valid IntegrationConfig is required')
    provider_code = config.integration.provider_code.lower()
    cls = GATEWAY_MAP.get(provider_code)
    if not cls:
        raise ValueError(f"Payment gateway '{provider_code}' is not supported")
    return cls(config)


def get_default_gateway(provider_code: str) -> PaymentGateway:
    config = IntegrationConfig.objects.filter(
        integration__provider_code__iexact=provider_code,
        is_active=True,
        is_default=True,
    ).first()
    if not config:
        raise LookupError(f"No active default integration config found for '{provider_code}'")
    return get_gateway(config)
