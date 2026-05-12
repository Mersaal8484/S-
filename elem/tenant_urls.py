from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.http import HttpResponse

urlpatterns = [
    path('tenant-test/', lambda r: HttpResponse("Tenant URLConf Active")),
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('billing/', include('billing.urls')),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/', include('billing.api.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
