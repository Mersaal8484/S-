from django import forms
from .models import (
    Contract, ContractLine, MeterReading, DateRange, DateRangeType,
    UoM, Journal, InvoiceTemplate, TaskQueue, Product, UoMCategory
)
from billing.models import Customer


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'contract_number', 'name', 'partner', 'partner_old_id',
            'meter_number', 'meter_type', 'meter_phase_type', 'meter_usage_type',
            'meter_first_reading', 'meter_multiplier',
            'recurring_invoices', 'recurring_rule_type', 'recurring_interval',
            'recurring_invoicing_type', 'recurring_next_date',
            'connection_date', 'contract_date', 'journal',
        ]
        widgets = {
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'partner': forms.Select(attrs={'class': 'form-control'}),
            'partner_old_id': forms.TextInput(attrs={'class': 'form-control'}),
            'meter_number': forms.TextInput(attrs={'class': 'form-control'}),
            'meter_type': forms.Select(attrs={'class': 'form-control'}),
            'meter_phase_type': forms.Select(attrs={'class': 'form-control'}),
            'meter_usage_type': forms.Select(attrs={'class': 'form-control'}),
            'meter_first_reading': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'meter_multiplier': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'recurring_invoices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recurring_rule_type': forms.Select(attrs={'class': 'form-control'}),
            'recurring_interval': forms.NumberInput(attrs={'class': 'form-control'}),
            'recurring_invoicing_type': forms.Select(attrs={'class': 'form-control'}),
            'recurring_next_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'connection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'journal': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['partner'].queryset = Customer.objects.filter(is_active=True)
        self.fields['journal'].queryset = Journal.objects.filter(is_active=True)
        for field in ['contract_number', 'partner', 'partner_old_id', 'meter_number',
                      'meter_multiplier', 'recurring_next_date', 'connection_date',
                      'contract_date', 'journal']:
            self.fields[field].required = False

    def clean_meter_multiplier(self):
        return self.cleaned_data.get('meter_multiplier') or 1


class ContractLineForm(forms.ModelForm):
    class Meta:
        model = ContractLine
        fields = [
            'product', 'description', 'quantity', 'unit_price', 'discount', 'uom',
            'is_template', 'contract_type', 'pricing_type', 'tier_from', 'tier_to',
            'sequence', 'is_active',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'uom': forms.Select(attrs={'class': 'form-control'}),
            'is_template': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'pricing_type': forms.Select(attrs={'class': 'form-control'}),
            'tier_from': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tier_to': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sequence': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        self.fields['uom'].queryset = UoM.objects.filter(is_active=True)
        for field in ['product', 'description', 'uom', 'contract_type', 'pricing_type',
                      'tier_from', 'tier_to', 'sequence']:
            self.fields[field].required = False


class MeterReadingForm(forms.ModelForm):
    class Meta:
        model = MeterReading
        fields = ['reading_date', 'current_reading', 'reading_type', 'notes']
        widgets = {
            'reading_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'current_reading': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reading_type': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['reading_type', 'notes']:
            self.fields[field].required = False


class DateRangeForm(forms.ModelForm):
    class Meta:
        model = DateRange
        fields = ['date_range_type', 'name', 'date_from', 'date_to', 'is_active']
        widgets = {
            'date_range_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DateRangeTypeForm(forms.ModelForm):
    class Meta:
        model = DateRangeType
        fields = ['name', 'allow_overlap', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'allow_overlap': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UoMForm(forms.ModelForm):
    class Meta:
        model = UoM
        fields = ['code', 'name', 'category', 'factor', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'factor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        self.fields['category'].queryset = UoMCategory.objects.all()


class JournalForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ['code', 'name', 'journal_type', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'journal_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class InvoiceTemplateForm(forms.ModelForm):
    class Meta:
        model = InvoiceTemplate
        fields = [
            'product', 'description', 'quantity', 'unit_price', 'discount', 'uom',
            'contract_type', 'pricing_type', 'is_active', 'tier_from', 'tier_to',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'uom': forms.Select(attrs={'class': 'form-control'}),
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'pricing_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tier_from': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tier_to': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        self.fields['uom'].queryset = UoM.objects.filter(is_active=True)
        for field in ['product', 'description', 'uom', 'contract_type', 'pricing_type',
                      'tier_from', 'tier_to']:
            self.fields[field].required = False


class TaskQueueForm(forms.ModelForm):
    class Meta:
        model = TaskQueue
        fields = ['name', 'task_type', 'payload', 'priority', 'scheduled_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'task_type': forms.Select(attrs={'class': 'form-control'}),
            'payload': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['priority'].required = False
        self.fields['scheduled_at'].required = False
