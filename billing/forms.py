from django import forms
from .models import Customer, Contract, Meter, SubscriptionType, BillingPeriod, MeterReadingSubmission, Invoice, Payment
import random
from datetime import datetime as dt


def generate_number(prefix, length=4):
    return f"{prefix}-{dt.now().strftime('%Y%m%d')}-{random.randint(10**(length-1), 10**length-1)}"


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['customer_number', 'full_name_ar', 'full_name_en', 'national_id',
                 'mobile_phone', 'phone2', 'email', 'address', 'city', 'is_active', 'credit_limit', 'notes']
        widgets = {
            'customer_number': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name_ar': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name_en': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'phone2': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['customer_number', 'full_name_ar', 'credit_limit']:
            self.fields[field].required = False
        if not self.instance.pk:
            self.fields['customer_number'].initial = generate_number('CUST')
            self.fields['credit_limit'].initial = 0
    
    def clean_customer_number(self):
        number = self.cleaned_data.get('customer_number')
        if not number:
            number = generate_number('CUST')
        return number
    
    def clean_credit_limit(self):
        return self.cleaned_data.get('credit_limit') or 0


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['contract_number', 'customer', 'type', 'start_date', 'end_date',
                 'contract_status', 'connection_load', 'deposit_amount', 'notes']
        widgets = {
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_status': forms.Select(attrs={'class': 'form-control'}),
            'connection_load': forms.NumberInput(attrs={'class': 'form-control'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True)
        self.fields['type'].queryset = SubscriptionType.objects.filter(is_active=True)
        for field in ['contract_number', 'end_date', 'connection_load', 'deposit_amount', 'contract_status']:
            self.fields[field].required = False
        if not self.instance.pk:
            self.initial['contract_number'] = generate_number('CTR')
            self.initial['start_date'] = dt.now().date()
    
    def clean_contract_number(self):
        number = self.cleaned_data.get('contract_number')
        if not number:
            number = generate_number('CTR')
        return number
    
    def clean_connection_load(self):
        return self.cleaned_data.get('connection_load') or 0
    
    def clean_deposit_amount(self):
        return self.cleaned_data.get('deposit_amount') or 0
    
    def clean_contract_status(self):
        return self.cleaned_data.get('contract_status') or 'active'

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        if end_date == '':
            return None
        return end_date


class MeterForm(forms.ModelForm):
    class Meta:
        model = Meter
        fields = ['meter_number', 'contract', 'meter_model', 'meter_type',
                  'initial_reading', 'installation_date', 'meter_status', 'location_description']
        widgets = {
            'meter_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contract': forms.Select(attrs={'class': 'form-control'}),
            'meter_model': forms.TextInput(attrs={'class': 'form-control'}),
            'meter_type': forms.Select(attrs={'class': 'form-control'}),
            'initial_reading': forms.NumberInput(attrs={'class': 'form-control'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'meter_status': forms.Select(attrs={'class': 'form-control'}),
            'location_description': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contract'].queryset = Contract.objects.filter(contract_status='active')
        for field in ['meter_number', 'initial_reading', 'meter_status']:
            self.fields[field].required = False
        if not self.instance.pk:
            self.initial['installation_date'] = dt.now().date()
            self.initial['initial_reading'] = 0
    
    def clean_meter_number(self):
        if not self.cleaned_data.get('meter_number'):
            import random
            return f"M-{random.randint(10000, 99999)}"
        return self.cleaned_data['meter_number']
    
    def clean_initial_reading(self):
        return self.cleaned_data.get('initial_reading') or 0
    
    def clean_meter_status(self):
        return self.cleaned_data.get('meter_status') or 'active'


class BillingPeriodForm(forms.ModelForm):
    class Meta:
        model = BillingPeriod
        fields = ['period_name', 'period_code', 'start_date', 'end_date',
                  'reading_start_date', 'reading_end_date', 'billing_cycle', 'status']
        widgets = {
            'period_name': forms.TextInput(attrs={'class': 'form-control'}),
            'period_code': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reading_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reading_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['contract', 'invoice', 'customer', 'amount', 'payment_method', 'period', 'reference_number', 'bank_name', 'notes']
        widgets = {
            'contract': forms.Select(attrs={'class': 'form-control'}),
            'invoice': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'period': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['invoice'].queryset = Invoice.objects.filter(
            invoice_status__in=['issued', 'partially_paid', 'overdue']
        )
        self.fields['contract'].queryset = Contract.objects.filter(contract_status='active')
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True)
        for field in ['payment_method']:
            self.fields[field].required = False
        if not self.instance.pk:
            self.initial['payment_date'] = dt.now().date()
    
    def clean_payment_method(self):
        return self.cleaned_data.get('payment_method') or 'cash'
    
    def clean_payment_date(self):
        return self.cleaned_data.get('payment_date') or dt.now().date()
    
    def clean(self):
        cleaned = super().clean()
        contract = cleaned.get('contract')
        customer = cleaned.get('customer')
        
        if contract and not customer:
            cleaned['customer'] = contract.customer
        
        return cleaned