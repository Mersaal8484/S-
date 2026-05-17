from abc import ABC, abstractmethod
from decimal import Decimal


class EWalletGateway(ABC):
    def __init__(self, provider):
        self.provider = provider

    @abstractmethod
    def initiate(self, wallet_number: str, amount: Decimal, ref: str) -> dict:
        pass

    @abstractmethod
    def verify(self, transaction_id: str) -> dict:
        pass


class STCPayGateway(EWalletGateway):
    def initiate(self, wallet_number, amount, ref):
        import requests
        resp = requests.post(self.provider.api_url, json={
            'MerchantId': self.provider.merchant_id,
            'BranchId': '1',
            'TellerId': '1',
            'DirectPaymentAuthorizeV4': {
                'MobileNumber': wallet_number,
                'Amount': str(amount),
                'RefNum': ref,
            }
        }, headers={'apikey': self.provider.api_key}, timeout=15)
        data = resp.json()
        return {
            'status': 'pending' if data.get('StatusCode') == '5000' else 'failed',
            'transaction_id': data.get('PaymentReference', ''),
            'redirect_url': '',
        }

    def verify(self, transaction_id):
        return {'status': 'pending', 'paid_at': None}


class TapGateway(EWalletGateway):
    def initiate(self, wallet_number, amount, ref):
        import requests
        resp = requests.post(f"{self.provider.api_url}/charges", json={
            'amount': float(amount),
            'currency': 'YER',
            'source': {'id': 'src_sa.mada'},
            'reference': {'merchant': ref},
        }, headers={'Authorization': f'Bearer {self.provider.api_key}'}, timeout=15)
        data = resp.json()
        return {
            'status': 'pending',
            'transaction_id': data.get('id', ''),
            'redirect_url': data.get('transaction', {}).get('url', ''),
        }

    def verify(self, transaction_id):
        return {'status': 'pending', 'paid_at': None}


GATEWAY_MAP = {
    'stc_pay': STCPayGateway,
    'tap':     TapGateway,
    'mada':    TapGateway,
}


def get_gateway(provider) -> EWalletGateway:
    cls = GATEWAY_MAP.get(provider.provider_code)
    if not cls:
        raise ValueError(f"Provider '{provider.provider_code}' غير مدعوم")
    return cls(provider)
