from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='accounting_dashboard'),

    # Accounts
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),

    # Journal Entries
    path('journal-entries/', views.journal_entry_list, name='journal_entry_list'),
    path('journal-entries/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal-entries/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('journal-entries/<int:pk>/post/', views.journal_entry_post, name='journal_entry_post'),

    # Bills (AP)
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/create/', views.bill_create, name='bill_create'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('bills/<int:pk>/edit/', views.bill_edit, name='bill_edit'),
    path('bills/<int:pk>/delete/', views.bill_delete, name='bill_delete'),
    path('bills/<int:pk>/post/', views.bill_post, name='bill_post'),

    # Invoices (AR)
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/<int:pk>/post/', views.invoice_post, name='invoice_post'),

    # Vendors
    path('vendors/', views.vendor_list, name='vendor_list'),
    path('vendors/create/', views.vendor_create, name='vendor_create'),
    path('vendors/<int:pk>/edit/', views.vendor_edit, name='vendor_edit'),
    path('vendors/<int:pk>/delete/', views.vendor_delete, name='vendor_delete'),
    path('vendors/<int:pk>/accounts/', views.vendor_accounts, name='vendor_accounts'),
    path('vendors/<int:pk>/add-account/', views.add_vendor_account, name='add_vendor_account'),
    path('vendors/<int:pk>/unlink-account/<int:account_pk>/', views.unlink_vendor_account, name='unlink_vendor_account'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customers/<int:pk>/accounts/', views.customer_accounts, name='customer_accounts'),
    path('customers/<int:pk>/add-account/', views.add_customer_account, name='add_customer_account'),
    path('customers/<int:pk>/unlink-account/<int:account_pk>/', views.unlink_customer_account, name='unlink_customer_account'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Reports
    path('ledger/', views.ledger, name='ledger'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('income-statement/', views.income_statement, name='income_statement'),
    path('analysis-accounts/', views.analysis_accounts, name='analysis_accounts'),
]
