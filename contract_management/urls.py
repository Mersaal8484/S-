from django.urls import path
from . import views

app_name = 'contract_management'

urlpatterns = [
    path('', views.contract_list, name='contract_list'),
    path('create/', views.contract_create, name='contract_create'),
    path('<int:pk>/', views.contract_detail, name='contract_detail'),
    path('<int:pk>/edit/', views.contract_edit, name='contract_edit'),
    path('<int:pk>/delete/', views.contract_delete, name='contract_delete'),
    path('<int:pk>/invoice-create/', views.contract_invoice_create, name='contract_invoice_create'),
    path('<int:pk>/create-reading/', views.meter_reading_create, name='meter_reading_create'),
    path('<int:contract_pk>/create-line/', views.contract_line_create, name='contract_line_create'),

    path('lines/<int:pk>/delete/', views.contract_line_delete, name='contract_line_delete'),
    path('readings/<int:pk>/delete/', views.meter_reading_delete, name='meter_reading_delete'),

    path('date-ranges/', views.date_range_list, name='date_range_list'),
    path('date-range-types/', views.date_range_type_list, name='date_range_type_list'),

    path('templates/', views.invoice_template_list, name='invoice_template_list'),
    path('templates/create/', views.invoice_template_create, name='invoice_template_create'),
    path('templates/<int:pk>/edit/', views.invoice_template_edit, name='invoice_template_edit'),

    path('journals/', views.journal_list, name='journal_list'),

    path('uoms/', views.uom_list, name='uom_list'),
    path('uoms/create/', views.uom_create, name='uom_create'),

    path('tasks/', views.task_queue_list, name='task_queue_list'),
    path('tasks/create/', views.task_queue_create, name='task_queue_create'),
    path('tasks/process-recurring/', views.process_recurring_invoices, name='process_recurring_invoices'),
]
