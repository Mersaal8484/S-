from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'customers', views.CustomerViewSet)
router.register(r'meters', views.MeterViewSet)
router.register(r'readings', views.ReadingViewSet)
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'routes', views.RouteViewSet)
router.register(r'route-assignments', views.RouteAssignmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('my-routes/', views.RouteAssignmentViewSet.as_view({'get': 'list'}), name='my-routes'),
    path('route-assignments/<int:assignment_id>/submit/',
         views.RouteExecutionSubmitView.as_view(), name='route-submit'),
    path('readings/pending/', views.ReadingViewSet.as_view({'get': 'pending'}), name='readings-pending'),
    path('ewallet/webhook/<str:provider_code>/',
         views.EWalletWebhookView.as_view(), name='ewallet-webhook'),
]
