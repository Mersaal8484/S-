from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.http import HttpResponse

urlpatterns = [
    path('public-test/', lambda r: HttpResponse("Public URLConf Active")),
    path('admin/', admin.site.urls),
    path('', include('tenants.urls')),
    path('stripe/', include('tenants.stripe_urls')),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]