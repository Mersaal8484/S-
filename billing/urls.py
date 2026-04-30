from django.urls import path
from . import views
from . i18n import set_language

urlpatterns = [
    path('', views.index, name='billing_index'),
    path('set-language/<str:lang>/', set_language, name='set_language'),
    
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_update'),
    
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('contracts/<int:pk>/', views.contract_detail, name='contract_detail'),
    path('contracts/<int:pk>/edit/', views.contract_update, name='contract_update'),
    
    path('meters/', views.meter_list, name='meter_list'),
    path('meters/create/', views.meter_create, name='meter_create'),
    path('meters/<int:pk>/edit/', views.meter_edit, name='meter_edit'),
    
    path('periods/', views.billing_period_list, name='billing_period_list'),
    path('periods/create/', views.billing_period_create, name='billing_period_create'),
    path('periods/<int:pk>/edit/', views.billing_period_edit, name='billing_period_edit'),
    path('periods/<int:pk>/close/', views.close_period, name='close_period'),
    
    path('readings/', views.reading_list, name='reading_list'),
    path('readings/create/', views.reading_create, name='reading_create'),
    path('readings/<int:pk>/approve/', views.reading_approve, name='reading_approve'),
    
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/print/', views.invoice_print, name='invoice_print'),
    path('invoices/<int:pk>/regenerate/', views.invoice_regenerate, name='invoice_regenerate'),
    
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    
    path('collectors/', views.collector_list, name='collector_list'),
    path('collectors/create/', views.collector_create, name='collector_create'),
    
    path('routes/', views.route_list, name='route_list'),
    path('routes/create/', views.route_create, name='route_create'),
    path('routes/<int:pk>/', views.route_detail, name='route_detail'),
    path('routes/<int:route_id>/add-contract/', views.route_add_contract, name='route_add_contract'),
    path('routes/<int:route_id>/remove/<int:contract_id>/', views.route_remove_contract, name='route_remove_contract'),
    
path('sms/', views.sms_list, name='sms_list'),
    path('sms/create/', views.sms_create, name='sms_create'),
    path('sms/providers/', views.sms_provider_list, name='sms_provider_list'),
    path('sms/providers/create/', views.sms_provider_create, name='sms_provider_create'),
    path('sms/templates/', views.sms_template_list, name='sms_template_list'),
    path('sms/templates/create/', views.sms_template_create, name='sms_template_create'),
    path('sms/templates/<int:pk>/', views.sms_template_edit, name='sms_template_edit'),
    
    path('settings/', views.system_settings, name='system_settings'),
    path('settings/subscription-types/create/', views.subscription_type_create, name='subscription_type_create'),
    path('settings/subscription-types/<int:pk>/edit/', views.subscription_type_edit, name='subscription_type_edit'),
    path('settings/templates/', views.template_list, name='template_list'),
    path('settings/templates/create/', views.template_create, name='template_create'),
    path('settings/templates/<int:pk>/', views.template_edit, name='template_edit'),
    path('settings/templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('settings/templates/create-for-type/<int:type_id>/', views.template_create_for_type, name='template_create_for_type'),
    
    path('ledger/', views.ledger_list, name='ledger_list'),
    path('ledger/<int:pk>/', views.ledger_detail, name='ledger_detail'),
    
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
]