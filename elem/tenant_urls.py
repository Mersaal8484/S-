from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.http import HttpResponse
from tenants.views import tenant_dashboard

urlpatterns = [
    path('tenant-test/', lambda r: HttpResponse("Tenant URLConf Active")),
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='tenant_root'),
    path('settings/', tenant_dashboard, name='tenant_dashboard_settings'),
    path('admin/', tenant_dashboard, name='tenant_dashboard'),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('billing.urls')),  # Merged directly - no /billing/ prefix
    path('', include('main.urls')),
    path('contracts/', include('contract_management.urls')),
    path('integrations/', include('integrations.urls')),
    path('accounting/', include('accounting.urls')),
    path('notifications/', include('notifications.urls')),
    path('reports/', include('reports.urls')),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/', include('billing.api.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
