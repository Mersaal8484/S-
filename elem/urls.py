from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tenants.urls')),
    path('stripe/', include('tenants.stripe_urls')),
]