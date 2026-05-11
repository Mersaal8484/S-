from rest_framework import serializers
from billing.models import (
    Customer, Contract, Meter, MeterReadingSubmission,
    Invoice, InvoiceLine, Payment, Route, RouteAssignment,
    RouteContract, RouteExecution, CustomerEWallet, EWalletTransaction
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class CustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'customer_number', 'full_name_ar', 'full_name_en',
                  'mobile_phone', 'city', 'current_balance', 'is_active']


class ContractSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name_ar', read_only=True)

    class Meta:
        model = Contract
        fields = '__all__'


class MeterSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(source='contract.contract_number', read_only=True)

    class Meta:
        model = Meter
        fields = '__all__'


class MeterReadingSubmissionSerializer(serializers.ModelSerializer):
    meter_number = serializers.CharField(source='meter.meter_number', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name_ar', read_only=True)

    class Meta:
        model = MeterReadingSubmission
        fields = '__all__'
        read_only_fields = ['previous_reading', 'approval_status',
                            'reviewed_by', 'reviewed_at', 'approved_reading',
                            'final_consumption', 'is_locked']


class MeterReadingSubmitSerializer(serializers.Serializer):
    meter_id = serializers.IntegerField()
    submitted_reading = serializers.DecimalField(max_digits=12, decimal_places=2)
    reading_date = serializers.DateField(required=False)
    reader_notes = serializers.CharField(required=False, allow_blank=True)
    meter_image = serializers.ImageField(required=False)
    gps_latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    gps_longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='contract.customer.full_name_ar', read_only=True)
    contract_number = serializers.CharField(source='contract.contract_number', read_only=True)
    remaining = serializers.DecimalField(source='remaining_amount', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = '__all__'


class InvoiceDetailSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='contract.customer.full_name_ar', read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name_ar', read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = '__all__'


class RouteAssignmentSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source='route.route_name_ar', read_only=True)

    class Meta:
        model = RouteAssignment
        fields = '__all__'


class RouteContractSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='contract.customer.full_name_ar', read_only=True)
    meter_number = serializers.CharField(source='contract.meters.first.meter_number', read_only=True)

    class Meta:
        model = RouteContract
        fields = '__all__'


class RouteExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteExecution
        fields = '__all__'


class RouteExecutionSubmitSerializer(serializers.Serializer):
    route_contract_id = serializers.IntegerField()
    actual_reading = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    gps_latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    gps_longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
    execution_status = serializers.ChoiceField(choices=['done', 'skipped'])
    skip_reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    meter_image = serializers.ImageField(required=False)


class CustomerEWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerEWallet
        fields = '__all__'


class EWalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EWalletTransaction
        fields = '__all__'
