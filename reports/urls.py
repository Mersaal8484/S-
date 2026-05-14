from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.reports_dashboard, name='dashboard'),
    
    # KPIs
    path('kpi/', views.kpi_dashboard, name='kpi_dashboard'),
    
    # Operational Reports
    path('consumption/', views.consumption_report, name='consumption'),
    path('collection/', views.collection_report, name='collection'),
    path('notifications/', views.notifications_report, name='notifications'),
    path('invoicing/', views.invoicing_report, name='invoicing'),
]
