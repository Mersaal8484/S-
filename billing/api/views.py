from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal

from billing.models import (
    Customer, Contract, Meter, MeterReadingSubmission,
    Invoice, InvoiceLine, Payment, Route, RouteAssignment,
    RouteContract, RouteExecution, CustomerEWallet, EWalletTransaction,
    EWalletProvider
)
from billing.services import (
    submit_meter_reading, approve_reading, record_payment, generate_invoice
)
from .serializers import (
    CustomerSerializer, CustomerListSerializer, ContractSerializer,
    MeterSerializer, MeterReadingSubmissionSerializer,
    MeterReadingSubmitSerializer, InvoiceSerializer,
    InvoiceDetailSerializer, PaymentSerializer,
    RouteSerializer, RouteAssignmentSerializer,
    RouteContractSerializer, RouteExecutionSerializer,
    RouteExecutionSubmitSerializer, CustomerEWalletSerializer,
    EWalletTransactionSerializer
)
from .permissions import TenantUserPermission, IsFieldReader, IsCollector, IsTenantAdmin
from core.ewallet_service import get_gateway
from core.barcode_service import meter_barcode_png, meter_qr_png
from django.http import HttpResponse


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    permission_classes = [TenantUserPermission]
    search_fields = ['customer_number', 'full_name_ar', 'mobile_phone']
    filterset_fields = ['city', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        return CustomerSerializer

    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        customer = self.get_object()
        invoices = Invoice.objects.filter(contract__customer=customer)
        page = self.paginate_queryset(invoices)
        serializer = InvoiceSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        customer = self.get_object()
        from billing.services import get_customer_balance
        return Response(get_customer_balance(customer))

    @action(detail=True, methods=['get'])
    def ewallets(self, request, pk=None):
        customer = self.get_object()
        ewallets = CustomerEWallet.objects.filter(customer=customer)
        serializer = CustomerEWalletSerializer(ewallets, many=True)
        return Response(serializer.data)


class MeterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Meter.objects.select_related('contract__customer').all()
    permission_classes = [TenantUserPermission]
    serializer_class = MeterSerializer
    search_fields = ['meter_number', 'contract__contract_number']
    filterset_fields = ['meter_status', 'meter_type']

    @action(detail=True, methods=['get'])
    def barcode(self, request, pk=None):
        meter = self.get_object()
        png = meter_barcode_png(meter.meter_number)
        return HttpResponse(png, content_type='image/png')

    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        meter = self.get_object()
        domain = request.get_host()
        png = meter_qr_png(meter.meter_number, domain)
        return HttpResponse(png, content_type='image/png')


class ReadingViewSet(viewsets.ModelViewSet):
    queryset = MeterReadingSubmission.objects.select_related(
        'meter', 'customer', 'period'
    ).all()
    permission_classes = [TenantUserPermission]
    filterset_fields = ['approval_status', 'period', 'reading_source']
    search_fields = ['meter__meter_number', 'customer__full_name_ar']

    def get_serializer_class(self):
        if self.action == 'create':
            return MeterReadingSubmitSerializer
        return MeterReadingSubmissionSerializer

    def create(self, request, *args, **kwargs):
        serializer = MeterReadingSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        meter = get_object_or_404(Meter, pk=serializer.validated_data['meter_id'])
        submission = submit_meter_reading(meter, {
            'current_reading': serializer.validated_data['submitted_reading'],
            'reading_date': serializer.validated_data.get('reading_date'),
            'reader_id': request.user.id,
            'notes': serializer.validated_data.get('reader_notes', ''),
        })

        output = MeterReadingSubmissionSerializer(submission)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        readings = self.queryset.filter(approval_status='pending')
        page = self.paginate_queryset(readings)
        serializer = MeterReadingSubmissionSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        reading = self.get_object()
        approved_reading = request.data.get('approved_reading', reading.submitted_reading)
        submission = approve_reading(reading, approved_reading, request.user)
        serializer = MeterReadingSubmissionSerializer(submission)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.select_related(
        'contract__customer', 'period'
    ).prefetch_related('lines').all()
    permission_classes = [TenantUserPermission]
    search_fields = ['invoice_number', 'contract__customer__full_name_ar']
    filterset_fields = ['invoice_status', 'period']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InvoiceDetailSerializer
        return InvoiceSerializer

    @action(detail=True, methods=['get'])
    def pay_options(self, request, pk=None):
        invoice = self.get_object()
        customer = invoice.contract.customer
        ewallets = CustomerEWallet.objects.filter(customer=customer, status='active')
        return Response({
            'invoice_id': invoice.id,
            'remaining': invoice.remaining_amount,
            'ewallets': CustomerEWalletSerializer(ewallets, many=True).data,
        })

    @action(detail=True, methods=['post'])
    def pay_ewallet(self, request, pk=None):
        invoice = self.get_object()
        ewallet_id = request.data.get('ewallet_id')
        ewallet = get_object_or_404(CustomerEWallet, pk=ewallet_id, customer=invoice.contract.customer)

        gateway = get_gateway(ewallet.provider)
        ref = f"INV-{invoice.invoice_number}"
        result = gateway.initiate(ewallet.wallet_number, invoice.remaining_amount, ref)

        payment = record_payment(invoice, invoice.remaining_amount, {
            'payment_method': 'online',
            'source_type': 'ewallet',
            'reference_number': result['transaction_id'],
        })

        EWalletTransaction.objects.create(
            payment=payment,
            ewallet=ewallet,
            transaction_reference=result['transaction_id'],
            transaction_amount=invoice.remaining_amount,
            transaction_status='pending',
        )

        return Response({
            'status': result['status'],
            'redirect_url': result.get('redirect_url', ''),
            'transaction_id': result['transaction_id'],
        })


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('customer', 'invoice').all()
    permission_classes = [TenantUserPermission]
    serializer_class = PaymentSerializer
    search_fields = ['payment_number', 'customer__full_name_ar']
    filterset_fields = ['payment_method', 'source_type']


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.prefetch_related('contracts__contract__customer').all()
    permission_classes = [TenantUserPermission]
    serializer_class = RouteSerializer


class RouteAssignmentViewSet(viewsets.ModelViewSet):
    queryset = RouteAssignment.objects.select_related('route').all()
    permission_classes = [TenantUserPermission, IsFieldReader]
    serializer_class = RouteAssignmentSerializer
    filterset_fields = ['status', 'assignment_date']

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = 'in_progress'
        from django.utils import timezone
        assignment.started_at = timezone.now()
        assignment.save()
        return Response({'status': 'in_progress'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = 'completed'
        from django.utils import timezone
        assignment.completed_at = timezone.now()
        assignment.save()
        return Response({'status': 'completed'})

    @action(detail=True, methods=['get'])
    def stops(self, request, pk=None):
        assignment = self.get_object()
        contracts = RouteContract.objects.filter(
            route=assignment.route
        ).select_related('contract__customer')
        serializer = RouteContractSerializer(contracts, many=True)
        return Response(serializer.data)


class RouteExecutionSubmitView(APIView):
    permission_classes = [TenantUserPermission, IsFieldReader]

    def post(self, request, assignment_id):
        assignment = get_object_or_404(RouteAssignment, pk=assignment_id)
        serializer = RouteExecutionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rc = get_object_or_404(
            RouteContract,
            pk=serializer.validated_data['route_contract_id'],
            route=assignment.route
        )

        with transaction.atomic():
            execution = RouteExecution.objects.create(
                assignment=assignment,
                route_contract=rc,
                stop_order=rc.stop_order,
                actual_reading=serializer.validated_data.get('actual_reading'),
                execution_status=serializer.validated_data['execution_status'],
                skip_reason=serializer.validated_data.get('skip_reason', ''),
                gps_latitude=serializer.validated_data.get('gps_latitude'),
                gps_longitude=serializer.validated_data.get('gps_longitude'),
                notes=serializer.validated_data.get('notes', ''),
            )

            if (execution.execution_status == 'done'
                    and execution.actual_reading is not None):
                meter = rc.contract.meters.filter(meter_status='active').first()
                if meter:
                    submit_meter_reading(meter, {
                        'current_reading': execution.actual_reading,
                        'reader_id': request.user.id,
                        'notes': f'Route {assignment.route.route_code}',
                    })

        return Response(RouteExecutionSerializer(execution).data,
                        status=status.HTTP_201_CREATED)


class EWalletWebhookView(APIView):
    permission_classes = []

    def post(self, request, provider_code):
        txn = get_object_or_404(
            EWalletTransaction,
            transaction_reference=request.data.get('reference')
        )
        if txn.transaction_status != 'completed':
            txn.transaction_status = 'completed'
            txn.save()
            from billing.services import record_payment
            record_payment(txn.payment.invoice, txn.net_amount, {
                'payment_method': 'online',
                'source_type': 'ewallet',
                'reference_number': txn.transaction_reference,
            })
        return Response({'status': 'ok'})
