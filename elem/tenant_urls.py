from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', include('main.urls')),
    path('billing/', include('billing.urls')),
    path('api/v1/', include('billing.api.urls')),
    path('api/v1/auth/', include('rest_framework_simplejwt.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
