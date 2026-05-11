from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('pricing/', views.pricing, name='pricing'),
    path('register/', views.register, name='register'),
    path('register/success/<int:tenant_id>/', views.register_success, name='register_success'),
]
