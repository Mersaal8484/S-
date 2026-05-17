from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('pricing/', views.pricing, name='pricing'),
    path('register/', views.register, name='register'),
    path('register/success/<int:tenant_id>/', views.register_success, name='register_success'),
    path('upgrade/<int:tenant_id>/', views.upgrade_checkout, name='upgrade_checkout'),
    path('upgrade/<int:tenant_id>/success/', views.upgrade_success, name='upgrade_success'),
    path('super-admin/dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('super-admin/settings/', views.platform_settings, name='platform_settings'),
    path('super-admin/plans/', views.plan_management, name='plan_management'),
]
