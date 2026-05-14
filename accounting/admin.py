from django.contrib import admin
from .models import (
    Account, Vendor, Customer, Product, JournalEntry, JournalLine,
    Bill, BillLine, Invoice, InvoiceLine, VendorAccount, CustomerAccount
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'parent', 'is_active', 'balance']
    list_filter = ['account_type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['vendor_code', 'name', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['vendor_code', 'name', 'email']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_code', 'name', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['customer_code', 'name', 'email']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'product_type', 'sale_price', 'cost_price', 'is_active']
    list_filter = ['product_type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'date', 'reference', 'is_posted', 'created_at']
    list_filter = ['is_posted']
    search_fields = ['entry_number', 'reference', 'description']


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ['journal_entry', 'account', 'debit', 'credit']
    list_filter = ['account']


class BillLineInline(admin.TabularInline):
    model = BillLine
    extra = 1


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'vendor', 'date', 'due_date', 'total_amount', 'status']
    list_filter = ['status']
    search_fields = ['bill_number', 'vendor__name']


@admin.register(BillLine)
class BillLineAdmin(admin.ModelAdmin):
    list_display = ['bill', 'product', 'description', 'quantity', 'unit_price', 'amount']
    list_filter = ['bill']


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'date', 'due_date', 'total_amount', 'status']
    list_filter = ['status']
    search_fields = ['invoice_number', 'customer__name']


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'description', 'quantity', 'unit_price', 'amount']
    list_filter = ['invoice']


@admin.register(VendorAccount)
class VendorAccountAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'account']
    list_filter = ['vendor', 'account']


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ['customer', 'account']
    list_filter = ['customer', 'account']
