# PROJECT_MAP.md — نظام S-B (SaaS Edition)
> **تاريخ الفحص:** مايو 2026 | **Staff Software Engineer / Tech Lead**  
> **النموذج:** Multi-Tenant SaaS | **العملاء:** شركات كهرباء/مياه خاصة (B2B)  
> **المستودع:** https://github.com/Mersaal8484/S-.git

---

## [TECH_STACK]

### الحالي (يجب الترقية/التغيير)

| المكون | الحالي | المشكلة |
|--------|--------|---------|
| DB Engine | SQLite | ❌ لا يدعم PostgreSQL Schemas — غير قابل للـ Multi-Tenancy |
| DB Adapter | — | ❌ مفقود psycopg2 |
| Tenant Layer | ❌ غير موجود | 37 نموذج بدون أي tenant isolation |
| Billing/Subscription | ❌ غير موجود | لا آلية لتحصيل اشتراك SaaS |
| Auth | Django Auth فقط | ⚠️ يحتاج tenant-aware |
| SECRET_KEY | مكشوف في الكود | ❌ خطر أمني حرج |
| SystemSettings | global (بدون tenant) | ❌ ستتداخل بيانات العملاء |

### المطلوب (مُوثَّق بالإصدارات الرسمية - مايو 2026)

```
# ===== CORE SAAS INFRASTRUCTURE =====
django==6.0.4                          # ✅ موجود
psycopg2-binary==2.9.12               # PostgreSQL adapter
django-tenants==3.10.1                 # Schema-based Multi-Tenancy
python-decouple==3.8                   # Environment variables

# ===== REST API =====
djangorestframework==3.17.1            # ✅ موجود في venv
djangorestframework-simplejwt==5.5.0   # JWT Auth
django-cors-headers==4.9.0             # CORS للموبايل/SPA
django-filter==25.2                    # Filtering للـ API

# ===== SAAS BILLING =====
stripe==15.1.0                         # دفع اشتراكات SaaS
dj-stripe==2.10.3                      # Django-Stripe integration

# ===== FIELD APP FEATURES =====
python-barcode==0.16.1                 # Barcode للعدادات
qrcode==8.2                            # QR Code
Pillow==12.2.0                         # Image processing

# ===== ASYNC & PERFORMANCE =====
celery==5.6.3                          # Background tasks (ضروري للـ SaaS)
redis==5.2.1                           # Celery broker + caching
django-redis==5.4.0                    # Django cache backend

# ===== MONITORING (لاحقاً) =====
sentry-sdk==2.29.1                     # Error tracking
```

---

## [SYSTEM_FLOW]

### تدفق SaaS الجديد — طبقتان

```
┌─────────────────────────────────────────────────────────────────┐
│                    PUBLIC SCHEMA (shared)                         │
│                   "schema: public"                                │
│                                                                   │
│  Tenant ──► TenantSubscription ──► Plan (basic/pro/enterprise)   │
│     │              │                                             │
│     │         Stripe Subscription                                │
│     │                                                            │
│  Domain ──► subdomain.yoursaas.com                              │
│                                                                   │
│  [كل ما يخص إدارة الـ SaaS نفسه يعيش هنا]                      │
└─────────────────────────────────────────────────────────────────┘
                          │
              [HTTP Request يصل بـ subdomain]
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              TENANT SCHEMA (per company)                          │
│           "schema: company_xyz"                                   │
│                                                                   │
│  Customer → Contract → Meter → BillingPeriod                    │
│                                     │                            │
│                         MeterReadingSubmission                   │
│                         [pending → approved]                     │
│                                     │                            │
│                                  Invoice                         │
│                         (InvoiceLineTemplate)                    │
│                                     │                            │
│                                  Payment                         │
│                         (cash/ewallet/collector)                 │
│                                     │                            │
│                              BalanceLedger                       │
│                                                                   │
│  [37 نموذج موجود — كلها تنتقل هنا بدون تعديل المنطق]           │
└─────────────────────────────────────────────────────────────────┘
```

### تدفق تسجيل عميل SaaS جديد:
```
1. زيارة landing page → اختيار الخطة
2. تعبئة بيانات الشركة → Stripe Checkout
3. [تلقائي] إنشاء Tenant + PostgreSQL Schema
4. إنشاء subdomain: company_name.yoursaas.com
5. إنشاء Super Admin للشركة
6. Onboarding: SubscriptionType + أول BillingPeriod
```

---

## [ARCHITECTURE]

### الهيكل الجديد بعد التحويل:

```
S-/ (Django Project: elem)
│
├── elem/
│   ├── settings.py          ← تغيير جذري: DATABASE_ROUTERS + TENANT_MODEL
│   ├── urls.py              ← إضافة: public URLs + tenant URLs
│   └── wsgi.py
│
├── tenants/                 ← ✨ APP جديد (Public Schema)
│   ├── models.py            ← Tenant, Domain, Plan, TenantSubscription
│   ├── views.py             ← Registration, Onboarding, Admin Portal
│   ├── signals.py           ← post_save → إنشاء schema تلقائياً
│   └── stripe_webhooks.py   ← معالجة أحداث Stripe
│
├── billing/                 ← ✅ يبقى كما هو (Tenant Schema)
│   ├── models.py            ← 37 نموذج — لا تغيير في المنطق
│   ├── services.py          ← لا تغيير
│   ├── views.py             ← لا تغيير في المنطق
│   └── api/                 ← ✨ إضافة جديدة
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       └── permissions.py
│
├── core/                    ← ✨ APP جديد للمشترك بين كل tenant
│   ├── middleware.py        ← TenantAwareJWT, FeatureFlag check
│   ├── logging.py           ← Async logger (non-blocking)
│   ├── barcode_service.py   ← توليد Barcode/QR
│   └── ewallet_service.py   ← Adapter للمحافظ الإلكترونية
│
└── templates/
    ├── public/              ← Landing page, Pricing, Registration
    └── billing/ (موجودة)
```

### قاعدة DB الجديدة — PostgreSQL Schemas:

```sql
-- ما يولّده django-tenants تلقائياً:

Schema: public
  ├── tenants_tenant          (الشركات المشتركة)
  ├── tenants_domain          (subdomains)
  ├── tenants_plan            (basic/pro/enterprise)
  ├── tenants_subscription    (اشتراك كل شركة)
  └── django_migrations       (public migrations فقط)

Schema: company_alfa
  ├── billing_customer
  ├── billing_contract
  ├── billing_meter
  ├── billing_invoice
  ├── billing_payment
  ├── billing_systemsettings  ← الآن per-tenant ✅
  └── ... (كل 37 نموذج)

Schema: company_beta
  └── ... (نفس الهيكل، بيانات مستقلة تماماً)
```

---

## [EXECUTION_LOG]

| التاريخ | المهمة | الحالة | النتيجة |
|--------|--------|--------|---------|
| 2026-05-12 | بدء Milestone 0 | ✅ اكتمل | إعداد البيئة (Settings, Decouple, Tenants App) |
| 2026-05-12 | بدء Milestone 1 | 🟢 جاري التنفيذ | تعريف النماذج وفصل الروابط |

## [ORPHANS & PENDING]


| العنصر | الحالة | القرار |
|--------|--------|--------|
| `templates/integrations/` | قوالب بدون app | تُدمج في `tenants/` |
| `templates/accounting/` | قوالب بدون app | يُقيَّم لاحقاً — خارج النطاق الحالي |
| `odoo/` | modules منفصلة | يبقى منفصل — integration اختيارية |
| `calculate_line_amount()` tiered | ✅ اكتمل | تم الإصلاح في خدمات billing |
| `BillingQueue` | بدون async processing | يُفعَّل بـ Celery في M4 |
| `SMSQueue` | بدون scheduler | يُفعَّل بـ Celery في M4 |
| `EWalletTransaction` | model بدون service | يُنفَّذ في M5 |
| SQLite → PostgreSQL | migration | أول خطوة في M0 |
| Offline sync للميدان | غير منفذ | PENDING — خارج النطاق |
