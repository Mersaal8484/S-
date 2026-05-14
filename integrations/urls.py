from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('', views.integration_list, name='integration_list'),
    path('register/', views.integration_register, name='integration_register'),
    path('<int:pk>/', views.integration_detail, name='integration_detail'),
    path('<int:integration_pk>/config/create/', views.integration_config_create, name='integration_config_create'),
    path('config/<int:pk>/edit/', views.integration_config_edit, name='integration_config_edit'),
    path('config/<int:pk>/delete/', views.integration_config_delete, name='integration_config_delete'),
    path('config/<int:config_pk>/logs/', views.integration_logs, name='integration_logs'),
]
