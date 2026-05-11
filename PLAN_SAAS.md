# PLAN.md — تحويل S-B إلى SaaS Multi-Tenant
> **Staff Software Engineer / Tech Lead**  
> **التاريخ:** مايو 2026 | **النموذج:** Multi-Tenant (PostgreSQL Schema Isolation)  
> **الهدف التجاري:** شركات كهرباء/مياه خاصة تشترك شهرياً بـ SaaS

---

## الافتراضات الصريحة (لا غموض)

1. **Multi-Tenancy:** كل شركة = PostgreSQL Schema مستقل — بيانات معزولة تماماً
2. **Subdomain routing:** `company1.yoursaas.com` / `company2.yoursaas.com`
3. **اشتراك SaaS:** يُدار بـ Stripe (الأكثر اكتمالاً، يدعم MENA عبر USD)
4. **المنطق الحالي في `billing/` يبقى بدون تغيير** — فقط نضيف طبقة tenant فوقه
5. **الأولوية:** الـ SaaS Infrastructure أولاً، الميزات الميدانية تتبعها

---

## نقطة الانطلاق الحرجة — لماذا `django-tenants`؟

```
SQLite الحالي → PostgreSQL مطلوب حتمياً
django-tenants يعمل على PostgreSQL Schemas
كل schema يحتوي نسخة كاملة من 37 نموذج billing
لا تعديل على models.py الحالية — فقط إضافة TENANT_APPS في settings
```

**البديل المرفوض:** إضافة `tenant = ForeignKey()` لكل نموذج → يُفسد 57 FK موجودة → خطر هائل

---

## [MILESTONE 0] — الأساس: PostgreSQL + البيئة الآمنة
**المدة:** يومان  
**Verifiable Goal:** `manage.py migrate_schemas --shared` ينجح، public schema يُنشأ في PostgreSQL

### 0.1 — تثبيت المتطلبات الجوهرية

```bash
pip install \
  psycopg2-binary==2.9.12 \
  django-tenants==3.10.1 \
  python-decouple==3.8 \
  djangorestframework==3.17.1 \
  djangorestframework-simplejwt==5.5.0 \
  django-cors-headers==4.9.0 \
  django-filter==25.2 \
  python-barcode==0.16.1 \
  qrcode==8.2 \
  Pillow==12.2.0 \
  redis==5.2.1 \
  celery==5.6.3 \
  stripe==15.1.0 \
  dj-stripe==2.10.3
```

### 0.2 — إنشاء `.env` وإصلاح الأمان

```bash
# .env
SECRET_KEY=<generated-64-chars>
DEBUG=False
ALLOWED_HOSTS=.yoursaas.com,localhost

DATABASE_URL=postgresql://user:pass@localhost:5432/saas_billing_db

STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

REDIS_URL=redis://localhost:6379/0
```

```python
# elem/settings.py
from decouple import config, Csv
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool, default=False)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
```

### 0.3 — إعداد PostgreSQL في settings.py

```python
# elem/settings.py — التغييرات الجوهرية

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

TENANT_MODEL = 'tenants.Tenant'
TENANT_DOMAIN_MODEL = 'tenants.Domain'

# Apps في الـ PUBLIC schema فقط
SHARED_APPS = [
    'django_tenants',
    'tenants',           # APP الجديد
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djstripe',          # SaaS billing
]

# Apps في كل TENANT schema
TENANT_APPS = [
    'billing',           # ✅ كل الـ 37 نموذج تنتقل هنا بدون تعديل
    'bootstrap4',
    'crispy_forms',
    'rest_framework',
    'django_filters',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
```

### 0.4 — إصلاح منطق tiered_kwh (خطأ موجود)

```python
# billing/services.py — استبدال calculate_line_amount()

def calculate_line_amount(template, consumption):
    from decimal import Decimal

    if template.calculation_type == 'fixed':
        return template.fixed_amount or Decimal(0)

    elif template.calculation_type == 'single_rate_kwh':
        return (template.fixed_amount or Decimal(0)) * consumption

    elif template.calculation_type == 'tiered_kwh':
        # ✅ الإصلاح: حساب شرائح متدرجة حقيقية
        total = Decimal(0)
        remaining = consumption
        for detail in template.formula_details.order_by('min_value'):
            if remaining <= 0:
                break
            tier_max = detail.max_value or Decimal('9999999')
            tier_min = detail.min_value or Decimal(0)
            available = min(remaining, tier_max - tier_min)
            total += available * detail.rate_or_amount
            remaining -= available
        return total

    elif template.calculation_type == 'percentage':
        # يحتاج base_amount من السطر السابق — يُمرر لاحقاً
        return Decimal(0)

    elif template.calculation_type in ('demand_charge', 'minimum_charge'):
        return template.fixed_amount or Decimal(0)

    return Decimal(0)
```

**Verifiable Goal:** unit test يُثبت أن 350 kWh بشرائح 0-200@0.10 + 201-500@0.15 = 42.50 وليس 52.50

---

## [MILESTONE 1] — Tenant Infrastructure
**المدة:** 3 أيام  
**Verifiable Goal:** شركتان مسجلتان، كل واحدة لها schema مستقل، البيانات لا تتداخل

### 1.1 — إنشاء `tenants/` APP

```python
# tenants/models.py

from django_tenants.models import TenantMixin, DomainMixin
from django.db import models


class Plan(models.Model):
    """خطط اشتراك SaaS"""
    class PlanTier(models.TextChoices):
        BASIC = 'basic', 'Basic'           # حتى 1000 مشترك
        PRO = 'pro', 'Pro'                 # حتى 10,000 مشترك
        ENTERPRISE = 'enterprise', 'Enterprise'  # غير محدود

    name = models.CharField(max_length=50)
    tier = models.CharField(max_length=20, choices=PlanTier.choices)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    max_customers = models.IntegerField(default=1000)
    max_meters = models.IntegerField(default=5000)
    max_users = models.IntegerField(default=10)
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    features = models.JSONField(default=dict)  # {'sms': True, 'ewallet': True, 'api': True}
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.price_monthly}/شهر"


class Tenant(TenantMixin):
    """شركة مشتركة في النظام"""
    company_name = models.CharField(max_length=200)
    company_name_ar = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=2, default='SA')  # ISO 3166
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('trialing', 'Trial'),
            ('active', 'Active'),
            ('past_due', 'Past Due'),
            ('canceled', 'Canceled'),
        ],
        default='trialing'
    )
    trial_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    # django-tenants: إنشاء schema تلقائي عند الحفظ
    auto_create_schema = True

    def __str__(self):
        return self.company_name


class Domain(DomainMixin):
    """Subdomain لكل tenant: company.yoursaas.com"""
    pass
```

### 1.2 — Tenant Middleware (URL Routing)

```python
# elem/urls.py

# PUBLIC urls (landing, registration, stripe webhooks)
from django.urls import path, include

urlpatterns = [
    path('', include('tenants.urls')),                    # Landing + Registration
    path('stripe/', include('tenants.stripe_urls')),      # Stripe webhooks
    path('admin/', admin.site.urls),
]

# TENANT urls (داخل كل schema) — ملف منفصل
# elem/tenant_urls.py
urlpatterns = [
    path('', include('main.urls')),
    path('billing/', include('billing.urls')),
    path('api/v1/', include('billing.api.urls')),
    path('api/v1/auth/', include('rest_framework_simplejwt.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
```

```python
# elem/settings.py
ROOT_URLCONF = 'elem.urls'
PUBLIC_SCHEMA_URLCONF = 'elem.urls'
TENANT_URLCONF = 'elem.tenant_urls'   # ← جديد

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # ← أول middleware
    # ... باقي middleware
]
```

### 1.3 — Tenant Registration Flow

```
GET  /                          → Landing Page (Public)
GET  /pricing/                  → Plans + Pricing
POST /register/                 → إنشاء Tenant + Stripe Customer
GET  /register/checkout/{plan}/ → Stripe Checkout Session
POST /stripe/webhook/           → معالجة payment_intent.succeeded
     → إنشاء Schema + Domain + Super Admin
GET  /register/success/         → توجيه لـ subdomain الجديد
```

**Verifiable Goal:** تسجيل شركتين، `psql -c "\dn"` يُظهر `public`, `company_alfa`, `company_beta`

---

## [MILESTONE 2] — SaaS Billing (Stripe Integration)
**المدة:** 3 أيام  
**Verifiable Goal:** Trial ينتهي → Stripe يُرسل webhook → الحساب يتوقف تلقائياً

### 2.1 — Plans في Stripe Dashboard

```
Basic:      $49/شهر  أو $490/سنة
Pro:        $149/شهر أو $1490/سنة
Enterprise: تفاوض مباشر
```

### 2.2 — Stripe Webhook Handler

```python
# tenants/stripe_webhooks.py

import stripe
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)

    handlers = {
        'customer.subscription.created':  handle_subscription_created,
        'customer.subscription.updated':  handle_subscription_updated,
        'customer.subscription.deleted':  handle_subscription_deleted,
        'invoice.payment_succeeded':      handle_payment_succeeded,
        'invoice.payment_failed':         handle_payment_failed,
    }

    handler = handlers.get(event['type'])
    if handler:
        handler(event['data']['object'])

    return HttpResponse(status=200)


def handle_subscription_deleted(subscription):
    """تعليق الحساب عند إلغاء الاشتراك"""
    tenant = Tenant.objects.get(stripe_subscription_id=subscription['id'])
    tenant.subscription_status = 'canceled'
    tenant.is_active = False
    tenant.save()
    # لا حذف للـ schema — البيانات تبقى 90 يوماً
```

### 2.3 — Feature Flags بالخطة

```python
# core/middleware.py

class FeatureFlagMiddleware:
    """يمنع الوصول لميزات غير متاحة في الخطة الحالية"""

    FEATURE_MAP = {
        'api_access': ['pro', 'enterprise'],
        'ewallet':    ['pro', 'enterprise'],
        'sms':        ['basic', 'pro', 'enterprise'],
        'field_app':  ['pro', 'enterprise'],
        'barcode':    ['basic', 'pro', 'enterprise'],
    }

    def __call__(self, request):
        if hasattr(request, 'tenant') and request.tenant:
            plan_tier = request.tenant.plan.tier if request.tenant.plan else None
            request.available_features = {
                feature: plan_tier in tiers
                for feature, tiers in self.FEATURE_MAP.items()
            }
        return self.get_response(request)
```

**Verifiable Goal:** شركة Basic تحاول الوصول لـ `/api/v1/` → 403 Forbidden مع رسالة "الخطة الحالية لا تدعم API"

---

## [MILESTONE 3] — REST API + JWT (Tenant-Aware)
**المدة:** 3 أيام  
**Verifiable Goal:** Token يعمل فقط داخل subdomain الصحيح — لا cross-tenant access

### 3.1 — هيكل `billing/api/`

```
billing/api/
├── __init__.py
├── serializers.py      # ModelSerializer لكل نموذج رئيسي
├── views.py            # ViewSets — تستدعي services.py فقط
├── urls.py             # DefaultRouter
└── permissions.py      # IsFieldReader, IsCollector, IsTenantAdmin
```

**قاعدة صارمة:** لا منطق في api/views.py — كل استدعاء يمر عبر services.py القائم

### 3.2 — Tenant-Aware JWT

```python
# billing/api/permissions.py

from rest_framework.permissions import BasePermission

class TenantUserPermission(BasePermission):
    """
    يضمن أن المستخدم ينتمي للـ tenant الحالي
    django-tenants يضبط connection.schema_name تلقائياً
    — لا حاجة لتحقق إضافي إذا استُخدم الـ middleware الصحيح
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # كل query تعمل داخل schema الـ tenant — Django يعزل تلقائياً
        return True
```

### 3.3 — Endpoints المطلوبة

```
# Auth
POST /api/v1/auth/token/                → JWT access + refresh
POST /api/v1/auth/token/refresh/        → تجديد token

# Customers
GET  /api/v1/customers/                 → قائمة (مع pagination + filter)
POST /api/v1/customers/                 → إنشاء
GET  /api/v1/customers/{id}/            → تفاصيل
GET  /api/v1/customers/{id}/invoices/   → فواتير العميل
GET  /api/v1/customers/{id}/balance/    → الرصيد

# Meters
GET  /api/v1/meters/                    → قائمة
GET  /api/v1/meters/{id}/barcode/       → PNG barcode
GET  /api/v1/meters/{id}/qr/            → PNG QR code
POST /api/v1/meters/scan/               → تحقق من رقم العداد عبر barcode

# Readings (Field App محور العمل)
GET  /api/v1/readings/                  → قائمة
POST /api/v1/readings/                  → تقديم قراءة جديدة
POST /api/v1/readings/{id}/upload-image/ → رفع صورة العداد
GET  /api/v1/readings/pending/          → قراءات بانتظار المراجعة
POST /api/v1/readings/{id}/approve/     → موافقة (للمشرف)

# Invoices
GET  /api/v1/invoices/                  → قائمة
GET  /api/v1/invoices/{id}/             → تفاصيل مع البنود
GET  /api/v1/invoices/{id}/pay-options/ → خيارات الدفع المتاحة

# Payments
POST /api/v1/payments/                  → تسجيل دفعة
GET  /api/v1/payments/{id}/             → تفاصيل

# Routes (الميداني)
GET  /api/v1/my-routes/                 → مسارات اليوم للقارئ الحالي
POST /api/v1/route-assignments/{id}/start/    → بدء مسار
POST /api/v1/route-assignments/{id}/complete/ → إنهاء مسار
GET  /api/v1/route-assignments/{id}/stops/    → قائمة العدادات بالمسار
POST /api/v1/route-executions/{id}/submit/    → تقديم قراءة + صورة + GPS

# E-Wallet
GET  /api/v1/customers/{id}/ewallets/   → محافظ العميل
POST /api/v1/invoices/{id}/pay-ewallet/ → دفع عبر محفظة
POST /api/v1/ewallet/webhook/{provider}/ → Webhook من provider
```

**Verifiable Goal:** Postman Collection تُغطي كل endpoint، token من شركة A لا يعمل على subdomain شركة B

---

## [MILESTONE 4] — Barcode + QR + صور العدادات
**المدة:** 2 أيام  
**Verifiable Goal:** بطاقة عداد تُطبع بـ PDF تحتوي Barcode قابل للمسح

### 4.1 — Barcode Service (في `core/`)

```python
# core/barcode_service.py

import barcode
import qrcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64


def meter_barcode_png(meter_number: str) -> bytes:
    """Code128 — الأمثل للأرقام الأبجدية الرقمية"""
    writer = ImageWriter()
    code = barcode.get('code128', meter_number, writer=writer)
    buf = BytesIO()
    code.write(buf, options={
        'module_width': 0.2,
        'module_height': 15.0,
        'font_size': 8,
        'write_text': True,
    })
    return buf.getvalue()


def meter_qr_png(meter_number: str, tenant_domain: str) -> bytes:
    """QR يوجه لصفحة تفاصيل العداد"""
    url = f"https://{tenant_domain}/billing/meters/?search={meter_number}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
```

### 4.2 — صور العداد

```python
# إضافة لـ billing/models.py — MeterReadingSubmission
meter_image = models.ImageField(
    upload_to='readings/%Y/%m/tenant_{tenant_schema}/',
    null=True, blank=True
)
image_captured_at = models.DateTimeField(null=True, blank=True)
```

```python
# elem/settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # في الإنتاج → S3/Object Storage
```

### 4.3 — SystemSettings للتحكم (per-tenant)

```
# كل tenant يضبط هذه الإعدادات بشكل مستقل في قاعدته:
BARCODE_ENABLED          = 'true'
QR_ENABLED               = 'true'
METER_IMAGE_ENABLED      = 'true'
METER_IMAGE_REQUIRED     = 'false'   # إجباري أم اختياري
```

**Verifiable Goal:** SystemSettings لشركة A = true، لشركة B = false — لا تداخل

---

## [MILESTONE 5] — E-Wallet Integration
**المدة:** 3 أيام  
**Verifiable Goal:** دفع sandbox ينهي Invoice → status=paid، EWalletTransaction → completed

### 5.1 — Adapter Pattern (في `core/ewallet_service.py`)

```python
# core/ewallet_service.py

from abc import ABC, abstractmethod
from decimal import Decimal


class EWalletGateway(ABC):
    def __init__(self, provider):
        self.provider = provider

    @abstractmethod
    def initiate(self, wallet_number: str, amount: Decimal, ref: str) -> dict:
        """{'status': 'pending'|'completed'|'failed', 'transaction_id': str, 'redirect_url': str}"""

    @abstractmethod
    def verify(self, transaction_id: str) -> dict:
        """{'status': str, 'paid_at': datetime|None}"""


class STCPayGateway(EWalletGateway):
    def initiate(self, wallet_number, amount, ref):
        import requests
        resp = requests.post(self.provider.api_url, json={
            'MerchantId': self.provider.merchant_id,
            'BranchId': '1',
            'TellerId': '1',
            'DirectPaymentAuthorizeV4': {
                'MobileNumber': wallet_number,
                'Amount': str(amount),
                'RefNum': ref,
            }
        }, headers={'apikey': self.provider.api_key}, timeout=15)
        data = resp.json()
        return {
            'status': 'pending' if data.get('StatusCode') == '5000' else 'failed',
            'transaction_id': data.get('PaymentReference', ''),
            'redirect_url': '',
        }

    def verify(self, transaction_id):
        # polling endpoint STC Pay
        ...


class TapGateway(EWalletGateway):
    """يدعم: مدى، KNET، Benefit، Fawry"""
    def initiate(self, wallet_number, amount, ref):
        import requests
        resp = requests.post(f"{self.provider.api_url}/charges", json={
            'amount': float(amount),
            'currency': 'SAR',
            'source': {'id': 'src_sa.mada'},
            'reference': {'merchant': ref},
        }, headers={'Authorization': f'Bearer {self.provider.api_key}'}, timeout=15)
        data = resp.json()
        return {
            'status': 'pending',
            'transaction_id': data.get('id', ''),
            'redirect_url': data.get('transaction', {}).get('url', ''),
        }

    def verify(self, transaction_id):
        ...


GATEWAY_MAP = {
    'stc_pay': STCPayGateway,
    'tap':     TapGateway,
    'mada':    TapGateway,
}


def get_gateway(provider) -> EWalletGateway:
    cls = GATEWAY_MAP.get(provider.provider_code)
    if not cls:
        raise ValueError(f"Provider '{provider.provider_code}' غير مدعوم")
    return cls(provider)
```

### 5.2 — Payment Flow (يستدعي services.py الحالي)

```python
# billing/api/views.py

class InvoiceEWalletPayView(APIView):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        ewallet = get_object_or_404(CustomerEWallet,
                                    pk=request.data['ewallet_id'],
                                    customer=invoice.contract.customer)
        gateway = get_gateway(ewallet.provider)
        ref = f"INV-{invoice.invoice_number}"

        result = gateway.initiate(ewallet.wallet_number, invoice.remaining_amount, ref)

        EWalletTransaction.objects.create(
            payment=None,  # يُربط بعد الـ webhook
            ewallet=ewallet,
            transaction_reference=result['transaction_id'],
            transaction_amount=invoice.remaining_amount,
            transaction_status='pending',
        )

        return Response({
            'status': result['status'],
            'redirect_url': result.get('redirect_url', ''),
            'transaction_id': result['transaction_id'],
        })


class EWalletWebhookView(APIView):
    """يستقبل تأكيد الدفع من الـ provider"""
    permission_classes = []  # public endpoint — يُحقق بـ signature

    def post(self, request, provider_code):
        # التحقق من signature الـ provider
        # تحديث EWalletTransaction → completed
        # استدعاء record_payment() من services.py
        txn = EWalletTransaction.objects.get(
            transaction_reference=request.data.get('reference')
        )
        if txn.transaction_status != 'completed':
            txn.transaction_status = 'completed'
            txn.save()
            # استدعاء الـ service الحالي — لا تغيير في المنطق
            from billing.services import record_payment
            record_payment(txn.payment.invoice, txn.net_amount, {
                'payment_method': 'online',
                'source_type': 'ewallet',
                'reference_number': txn.transaction_reference,
            })
        return Response({'status': 'ok'})
```

---

## [MILESTONE 6] — Celery + Redis (Async Tasks)
**المدة:** 2 أيام  
**Verifiable Goal:** إنشاء 100 فاتورة لا يُبطئ HTTP response — يعمل في الخلفية

### لماذا Celery ضروري للـ SaaS؟

```
1. إرسال SMS → لا تنتظر الـ HTTP response
2. إغلاق فترة فوترة → 10,000 فاتورة لا تُعطل الطلب
3. تذكيرات الدفع → Scheduled tasks
4. Stripe webhooks processing → async لا sync
5. توليد Barcode batch → في الخلفية
```

### 6.1 — Celery Configuration

```python
# elem/settings.py
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_TIMEZONE = 'Asia/Riyadh'
CELERY_TASK_ALWAYS_EAGER = config('CELERY_ALWAYS_EAGER', cast=bool, default=False)

CELERY_BEAT_SCHEDULE = {
    'check-overdue-invoices': {
        'task': 'billing.tasks.mark_overdue_invoices',
        'schedule': crontab(hour=1, minute=0),  # كل يوم 1 صباحاً
    },
    'send-payment-reminders': {
        'task': 'billing.tasks.send_payment_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
}
```

### 6.2 — Tasks الأساسية

```python
# billing/tasks.py

from celery import shared_task
from django_tenants.utils import schema_context

@shared_task
def generate_period_invoices_async(period_id, schema_name):
    """إنشاء فواتير فترة كاملة في الخلفية"""
    with schema_context(schema_name):
        from billing.models import BillingPeriod
        from billing.services import close_billing_period
        period = BillingPeriod.objects.get(pk=period_id)
        close_billing_period(period)


@shared_task
def send_sms_queue():
    """إرسال SMS المنتظرة عبر provider"""
    from billing.models import SMSQueue, SMSProvider
    # يُعالج SMSQueue الموجود فعلاً في DB
    pending = SMSQueue.objects.filter(status='pending')[:50]
    for sms in pending:
        _send_single_sms(sms)


@shared_task
def mark_overdue_invoices():
    """تحديث حالة الفواتير المتأخرة — يعمل عبر كل schemas"""
    from django_tenants.utils import get_tenant_model
    for tenant in get_tenant_model().objects.filter(is_active=True):
        with schema_context(tenant.schema_name):
            _mark_overdue_for_tenant()
```

**ملاحظة حرجة:** كل Celery task تعمل على tenant يجب أن تستخدم `schema_context(schema_name)` — وإلا تعمل على `public` schema بالخطأ

**Verifiable Goal:** `close_billing_period()` لـ 500 قراءة → HTTP response فوري، Celery worker يُنهي الفواتير في الخلفية

---

## [MILESTONE 7] — Tenant Admin Portal + Onboarding
**المدة:** 2 أيام  
**Verifiable Goal:** شركة جديدة تُكمل onboarding في 5 دقائق وترسل أول فاتورة

### 7.1 — Super Admin Dashboard (public schema)

```
yoursaas.com/admin/
├── قائمة الشركات المشتركة + حالة الاشتراك
├── إيرادات شهرية (MRR)
├── عدد المشتركين الكلي
├── Tenants بـ past_due (يحتاجون تدخل)
└── إنشاء tenant يدوياً (للعملاء Enterprise)
```

### 7.2 — Tenant Onboarding Wizard (داخل tenant schema)

```
الخطوة 1: بيانات الشركة (اسم، شعار، منطقة زمنية)
الخطوة 2: أنواع الاشتراك (سكني، تجاري، صناعي)
الخطوة 3: قوالب الفواتير (Fixed/Tiered/Single Rate)
الخطوة 4: إنشاء أول مشترك اختباري
الخطوة 5: تأكيد وبدء الاستخدام
```

---

## [MILESTONE 8] — Logging + Monitoring
**المدة:** يوم واحد  
**Verifiable Goal:** كل API call مُسجَّل بـ schema_name — لا خلط بين tenant logs

### Non-Blocking Logging Strategy

```python
# core/logging.py

import logging
from django.db import connection

logger = logging.getLogger('billing.api')


class TenantAwareFilter(logging.Filter):
    """يُضيف schema_name لكل log record"""
    def filter(self, record):
        record.tenant_schema = getattr(connection, 'schema_name', 'public')
        return True


# elem/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'tenant_aware': {'()': 'core.logging.TenantAwareFilter'},
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/app.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'filters': ['tenant_aware'],
            'formatter': 'json',
        },
    },
    'loggers': {
        'billing.api':      {'handlers': ['file'], 'level': 'INFO'},
        'billing.services': {'handlers': ['file'], 'level': 'WARNING'},
        'tenants':          {'handlers': ['file'], 'level': 'INFO'},
    }
}
```

**قاعدة:** Middleware لا يكتب في DB — فقط file. `BillingProcessLog` يُكتب فقط من services.py عند إنشاء الفواتير وإغلاق الفترات.

---

## ترتيب التنفيذ النهائي

```
Week 1:  M0 (PostgreSQL + أمان + إصلاح tiered) → M1 (Tenant Infrastructure)
Week 2:  M2 (Stripe SaaS Billing) → M3 (REST API)
Week 3:  M4 (Barcode + صور) → M5 (E-Wallet)
Week 4:  M6 (Celery) → M7 (Admin Portal) → M8 (Logging)
```

---

## `requirements.txt` الكامل (مُوثَّق مايو 2026)

```
# Core
Django==6.0.4
psycopg2-binary==2.9.12
django-tenants==3.10.1
python-decouple==3.8

# Frontend
django-bootstrap4==26.1
django-crispy-forms==2.6

# REST API
djangorestframework==3.17.1
djangorestframework-simplejwt==5.5.0
django-cors-headers==4.9.0
django-filter==25.2

# SaaS Billing
stripe==15.1.0
dj-stripe==2.10.3

# Auth
PyJWT==2.12.1

# Field App Features
python-barcode==0.16.1
qrcode==8.2
Pillow==12.2.0

# Async
celery==5.6.3
redis==5.2.1
django-redis==5.4.0
```

---

## قرارات معمارية صريحة — لا رجعة فيها

| القرار | الاختيار | المرفوض | السبب |
|--------|---------|---------|-------|
| Tenant Model | PostgreSQL Schema (django-tenants) | ForeignKey tenant_id | إضافة FK لـ 57 علاقة = تدمير الكود الحالي |
| SaaS Billing | Stripe | يدوي | الأنضج والأكثر اكتمالاً لـ subscriptions |
| Async | Celery + Redis | Django Background Tasks | SaaS يتطلب scheduled tasks عبر كل schemas |
| API Auth | JWT (tenant-aware) | Session | Stateless — ضروري للموبايل والـ multi-tenant |
| Media Storage | Local → Object Storage (مرحلة لاحقة) | DB blobs | لا تُحشر الصور في DB |
| Barcode | Code128 | QR فقط | Code128 أدق للمسح السريع في الميدان |
| E-Wallet | Adapter Pattern | Direct implementation | يسمح إضافة provider جديد بدون تعديل core |

---

## ما هو خارج النطاق — لا feature creep

- ❌ Mobile App نفسه (فقط REST API)
- ❌ OCR لقراءة أرقام العداد من الصورة
- ❌ Offline sync للقارئ الميداني
- ❌ تكامل Odoo (module مستقل)
- ❌ WhatsApp API (يضاف بعد SMS يستقر)
- ❌ GraphQL
- ❌ Kubernetes / Docker (البنية التحتية منفصلة)
