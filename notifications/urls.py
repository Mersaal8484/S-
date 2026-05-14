from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('create/', views.notification_create, name='notification_create'),
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('providers/', views.provider_list, name='provider_list'),
    path('providers/create/', views.provider_create, name='provider_create'),
    path('logs/sms/', views.sms_log_list, name='sms_log_list'),
]
