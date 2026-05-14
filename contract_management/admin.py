from django.contrib import admin
from .models import (
    Contract, ContractLine, MeterReading, DateRange, DateRangeType,
    UoM, UoMCategory, Journal, InvoiceTemplate, TaskQueue, Product
)


@admin.register(UoMCategory)
class UoMCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(UoM)
class UoMAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'factor', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'sku']


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'journal_type', 'is_active']
    list_filter = ['journal_type', 'is_active']
    search_fields = ['code', 'name']


class ContractLineInline(admin.TabularInline):
    model = ContractLine
    extra = 1


class MeterReadingInline(admin.TabularInline):
    model = MeterReading
    extra = 0
    readonly_fields = ['previous_reading', 'consumption', 'created_at']
    fields = ['reading_date', 'reading_type', 'previous_reading', 'current_reading', 'consumption', 'is_invoiced', 'notes']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        'contract_number', 'name', 'partner', 'meter_number',
        'meter_type', 'meter_usage_type', 'recurring_invoices', 'is_active'
    ]
    list_filter = ['meter_type', 'meter_phase_type', 'meter_usage_type', 'recurring_invoices', 'is_active']
    search_fields = ['contract_number', 'name', 'partner_old_id', 'meter_number']
    inlines = [ContractLineInline, MeterReadingInline]


@admin.register(ContractLine)
class ContractLineAdmin(admin.ModelAdmin):
    list_display = ['contract', 'product', 'quantity', 'unit_price', 'discount', 'is_active']
    list_filter = ['is_active', 'pricing_type']
    search_fields = ['contract__name', 'product__name', 'description']


@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = ['contract', 'reading_date', 'reading_type', 'current_reading', 'consumption', 'is_invoiced']
    list_filter = ['reading_type', 'is_invoiced']
    search_fields = ['contract__name', 'contract__meter_number']


@admin.register(DateRangeType)
class DateRangeTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'allow_overlap', 'is_active']
    list_filter = ['allow_overlap', 'is_active']
    search_fields = ['name']


class DateRangeInline(admin.TabularInline):
    model = DateRange
    extra = 1


@admin.register(DateRange)
class DateRangeAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_range_type', 'date_from', 'date_to', 'is_active']
    list_filter = ['date_range_type', 'is_active']
    search_fields = ['name']


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ['product', 'description', 'pricing_type', 'unit_price', 'contract_type', 'is_active']
    list_filter = ['pricing_type', 'contract_type', 'is_active']
    search_fields = ['product__name', 'description']


@admin.register(TaskQueue)
class TaskQueueAdmin(admin.ModelAdmin):
    list_display = ['name', 'task_type', 'status', 'priority', 'retry_count', 'max_retries', 'scheduled_at', 'created_at']
    list_filter = ['task_type', 'status']
    search_fields = ['name']
