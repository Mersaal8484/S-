from django import forms
from .models import (
    Account, Vendor, Customer, Product, JournalEntry,
    Bill, Invoice, VendorAccount, CustomerAccount
)
import random
from datetime import datetime as dt


def generate_number(prefix, length=4):
    return f"{prefix}-{dt.now().strftime('%Y%m%d')}-{random.randint(10**(length-1), 10**length-1)}"


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'parent', 'is_active', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Account.objects.filter(is_active=True)
        self.fields['parent'].required = False
        self.fields['code'].required = False
        if not self.instance.pk:
            self.fields['code'].initial = generate_number('ACC')

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            code = generate_number('ACC')
        return code


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['vendor_code', 'name', 'contact_person', 'phone', 'email', 'address', 'tax_id', 'is_active']
        widgets = {
            'vendor_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vendor_code'].required = False
        if not self.instance.pk:
            self.fields['vendor_code'].initial = generate_number('VEN')

    def clean_vendor_code(self):
        code = self.cleaned_data.get('vendor_code')
        if not code:
            code = generate_number('VEN')
        return code


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['customer_code', 'name', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'customer_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer_code'].required = False
        if not self.instance.pk:
            self.fields['customer_code'].initial = generate_number('CUS')
            self.fields.pop('is_active', None)

    def clean_customer_code(self):
        code = self.cleaned_data.get('customer_code')
        if not code:
            code = generate_number('CUS')
        return code


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'sku', 'barcode', 'internal_code', 'name', 'description', 'product_type', 'sale_price', 'cost_price', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'internal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'product_type': forms.Select(attrs={'class': 'form-control'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False
        if not self.instance.pk:
            self.fields['code'].initial = generate_number('PROD')

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            code = generate_number('PROD')
        return code

    def clean_sale_price(self):
        return self.cleaned_data.get('sale_price') or 0

    def clean_cost_price(self):
        return self.cleaned_data.get('cost_price') or 0


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['date', 'reference', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial['date'] = dt.now().date()


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['vendor', 'date', 'due_date', 'reference', 'status', 'notes']
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vendor'].queryset = Vendor.objects.filter(is_active=True)
        if not self.instance.pk:
            self.initial['date'] = dt.now().date()
            self.initial['due_date'] = dt.now().date()


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'date', 'due_date', 'reference', 'status', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True)
        if not self.instance.pk:
            self.initial['date'] = dt.now().date()
            self.initial['due_date'] = dt.now().date()
