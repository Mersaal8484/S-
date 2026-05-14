from django.contrib import admin
from .models import (
    SubscriptionType, Customer, Contract, Meter,
    InvoiceLineTemplate, InvoiceLineFormulaDetail, BillingPeriod,
    MeterReadingSubmission, MeterReading, Invoice, InvoiceLine,
    Payment, Penalty, CustomerBalance, BalanceLedger,
    FinancialAdjustment, MeterChangeLog, BillingQueue, BillingProcessLog,
    SMSProvider, SMSTemplate, SMSQueue, SMSLog,
    SystemSettings, Collector, CollectorCashbox,
    CollectorCashboxTransaction, CashDeposit,
    EWalletProvider, CustomerEWallet, EWalletTransaction,
    MeterReader, Route, RouteContract, RouteAssignment,
    RouteExecution, RouteTrackingLog,
)


@admin.register(SubscriptionType)
class SubscriptionTypeAdmin(admin.ModelAdmin):
    list_display = ['name_ar', 'name_en', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name_ar', 'name_en']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_number', 'full_name_ar', 'mobile_phone', 'city', 'is_active', 'current_balance']
    list_filter = ['is_active', 'city']
    search_fields = ['customer_number', 'full_name_ar', 'mobile_phone', 'national_id']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'customer', 'type', 'contract_status', 'start_date', 'end_date']
    list_filter = ['contract_status', 'type']
    search_fields = ['contract_number', 'customer__full_name_ar']


@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = ['meter_number', 'contract', 'meter_type', 'meter_status', 'installation_date']
    list_filter = ['meter_type', 'meter_status']
    search_fields = ['meter_number', 'contract__contract_number']


@admin.register(InvoiceLineTemplate)
class InvoiceLineTemplateAdmin(admin.ModelAdmin):
    list_display = ['line_name_ar', 'type', 'calculation_type', 'line_order', 'is_active']
    list_filter = ['calculation_type', 'is_active', 'type']
    search_fields = ['line_name_ar', 'line_name_en']


@admin.register(InvoiceLineFormulaDetail)
class InvoiceLineFormulaDetailAdmin(admin.ModelAdmin):
    list_display = ['template', 'min_value', 'max_value', 'rate_or_amount']


@admin.register(BillingPeriod)
class BillingPeriodAdmin(admin.ModelAdmin):
    list_display = ['period_name', 'period_code', 'start_date', 'end_date', 'status', 'billing_cycle']
    list_filter = ['status', 'billing_cycle']
    search_fields = ['period_name', 'period_code']


@admin.register(MeterReadingSubmission)
class MeterReadingSubmissionAdmin(admin.ModelAdmin):
    list_display = ['meter', 'submitted_reading', 'reading_date', 'approval_status', 'reader']
    list_filter = ['approval_status', 'reading_source']
    search_fields = ['meter__meter_number']


@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = ['meter', 'reading_date', 'previous_reading', 'current_reading', 'reading_source', 'is_billed']
    list_filter = ['reading_source', 'is_billed']
    search_fields = ['meter__meter_number']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'contract', 'issue_date', 'due_date', 'total_amount', 'invoice_status']
    list_filter = ['invoice_status']
    search_fields = ['invoice_number', 'contract__contract_number']


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'line_name_ar', 'quantity', 'rate', 'amount', 'line_order']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'customer', 'amount', 'payment_date', 'payment_method', 'source_type']
    list_filter = ['payment_method', 'source_type']
    search_fields = ['payment_number', 'customer__full_name_ar']


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'penalty_amount', 'penalty_days', 'calculated_date', 'is_paid']


@admin.register(CustomerBalance)
class CustomerBalanceAdmin(admin.ModelAdmin):
    list_display = ['customer', 'current_balance', 'credit_limit', 'last_updated']


@admin.register(BalanceLedger)
class BalanceLedgerAdmin(admin.ModelAdmin):
    list_display = ['customer', 'transaction_type', 'debit', 'credit', 'balance_after', 'transaction_date']
    list_filter = ['transaction_type']
    search_fields = ['customer__full_name_ar']


@admin.register(FinancialAdjustment)
class FinancialAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['adjustment_number', 'customer', 'adjustment_type', 'amount', 'is_approved']
    list_filter = ['adjustment_type', 'is_approved']


@admin.register(MeterChangeLog)
class MeterChangeLogAdmin(admin.ModelAdmin):
    list_display = ['contract', 'old_meter', 'new_meter', 'change_reason', 'change_date']


@admin.register(BillingQueue)
class BillingQueueAdmin(admin.ModelAdmin):
    list_display = ['period', 'contract', 'customer', 'queue_status', 'priority', 'retry_count']
    list_filter = ['queue_status']


@admin.register(BillingProcessLog)
class BillingProcessLogAdmin(admin.ModelAdmin):
    list_display = ['period', 'action', 'status', 'affected_records', 'created_at']


@admin.register(SMSProvider)
class SMSProviderAdmin(admin.ModelAdmin):
    list_display = ['provider_name', 'sender_name', 'is_active', 'priority', 'cost_per_sms']
    list_filter = ['is_active']


@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_type', 'title_ar', 'language', 'is_active']
    list_filter = ['template_type', 'language', 'is_active']


@admin.register(SMSQueue)
class SMSQueueAdmin(admin.ModelAdmin):
    list_display = ['customer', 'mobile_number', 'status', 'retry_count', 'scheduled_time', 'sent_at']
    list_filter = ['status']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['sms', 'provider_response_code', 'delivery_status', 'delivery_time']


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['setting_key', 'setting_value', 'updated_at']
    search_fields = ['setting_key']


@admin.register(Collector)
class CollectorAdmin(admin.ModelAdmin):
    list_display = ['collector_code', 'full_name_ar', 'mobile_phone', 'collector_status', 'commission_percent']
    list_filter = ['collector_status']


@admin.register(CollectorCashbox)
class CollectorCashboxAdmin(admin.ModelAdmin):
    list_display = ['collector', 'cashbox_name', 'current_balance', 'status']
    list_filter = ['status']


@admin.register(CollectorCashboxTransaction)
class CollectorCashboxTransactionAdmin(admin.ModelAdmin):
    list_display = ['cashbox', 'transaction_type', 'amount', 'balance_after', 'transaction_date']
    list_filter = ['transaction_type']


@admin.register(CashDeposit)
class CashDepositAdmin(admin.ModelAdmin):
    list_display = ['deposit_number', 'collector', 'deposit_amount', 'deposit_date', 'status', 'deposit_method']
    list_filter = ['status', 'deposit_method']


@admin.register(EWalletProvider)
class EWalletProviderAdmin(admin.ModelAdmin):
    list_display = ['provider_name', 'provider_code', 'is_active', 'transaction_fee_percent']
    list_filter = ['is_active']


@admin.register(CustomerEWallet)
class CustomerEWalletAdmin(admin.ModelAdmin):
    list_display = ['customer', 'provider', 'wallet_number', 'is_verified', 'is_primary', 'status']
    list_filter = ['status', 'is_verified', 'is_primary']


@admin.register(EWalletTransaction)
class EWalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['payment', 'ewallet', 'transaction_reference', 'transaction_amount', 'transaction_status', 'transaction_date']
    list_filter = ['transaction_status']


@admin.register(MeterReader)
class MeterReaderAdmin(admin.ModelAdmin):
    list_display = ['reader_code', 'full_name_ar', 'mobile_phone', 'region', 'reader_status']
    list_filter = ['reader_status', 'region']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['route_code', 'route_name_ar', 'route_type', 'region', 'is_active']
    list_filter = ['route_type', 'is_active']
    search_fields = ['route_name_ar', 'route_code']


@admin.register(RouteContract)
class RouteContractAdmin(admin.ModelAdmin):
    list_display = ['route', 'contract', 'stop_order', 'priority']


@admin.register(RouteAssignment)
class RouteAssignmentAdmin(admin.ModelAdmin):
    list_display = ['route', 'assignment_date', 'shift', 'status', 'assigned_by']
    list_filter = ['status', 'shift']


@admin.register(RouteExecution)
class RouteExecutionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'stop_order', 'execution_status', 'executed_at']
    list_filter = ['execution_status']


@admin.register(RouteTrackingLog)
class RouteTrackingLogAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'user', 'action_type', 'created_at']
    list_filter = ['action_type']
