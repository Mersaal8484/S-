# S-B SaaS Project

## Commands

- Run server: `.\venv\Scripts\python.exe manage.py runserver`
- Create migrations: `.\venv\Scripts\python.exe manage.py makemigrations`
- Apply migrations (shared): `.\venv\Scripts\python.exe manage.py migrate_schemas --shared`
- Apply migrations (tenant): `.\venv\Scripts\python.exe manage.py migrate_schemas`
- Create app: `.\venv\Scripts\python.exe manage.py startapp <app_name>`
- Seed plans: `.\venv\Scripts\python.exe manage.py seed_plans`
- Seed integrations: `.\venv\Scripts\python.exe manage.py seed_integrations`
- Seed subscription types: `.\venv\Scripts\python.exe manage.py seed_subscription_types`
- Superuser: `.\venv\Scripts\python.exe manage.py createsuperuser`
- Shell: `.\venv\Scripts\python.exe manage.py shell`
- Check: `.\venv\Scripts\python.exe manage.py check`

All commands use the Windows venv path `.\venv\Scripts\python.exe`.

## Tech Stack

- Django 6.0.4 + django-tenants 3.10.1 (PostgreSQL schema-per-tenant)
- DRF 3.17 + SimpleJWT 5.5 for REST API
- Celery 5.6 + Redis for async tasks (CELERY_TASK_ALWAYS_EAGER configurable via env)
- django-bootstrap4 for UI, django-crispy-forms for forms
- Python-decouple for env vars (`.env` file)
- **No lint/format tools configured** — no ruff, black, etc.
- **No test framework** — only Django TestCase placeholders
- **PostgreSQL required** — django-tenants does not support SQLite

## Schema Architecture

Project settings in `elem.settings`. Two URLconfs:
- `elem/urls.py` = Public schema routes
- `elem/tenant_urls.py` = Tenant schema routes (set as `ROOT_URLCONF`; `PUBLIC_SCHEMA_URLCONF` overrides)

### Public Schema (`SHARED_APPS`)

| App | Description |
|-----|-------------|
| `tenants` | Tenant, Plan, Domain, TenantSubscription models |
| `core` | Middleware, logging, barcode/QR, e-wallet adapters |
| `integrations` | Third-party integration registry (also accessible from tenant URLs) |

### Per-Tenant Schema (`TENANT_APPS`)

| App | Description |
|-----|-------------|
| `billing` | Core billing: customers, contracts, meters, invoices, payments, SMS, routes, collectors, e-wallets |
| `contract_management` | Service contracts with meter readings, recurring invoices, UoM |
| `accounting` | Double-entry: Chart of Accounts, Journal Entries, AP/AR |
| `notifications` | Multi-channel (SMS, WhatsApp, Email, Push) templates and providers |
| `reports` | Reporting views |
| `main` | Tenant landing page |
| `core` | Also in tenant schema (shared middleware, context processors, templatetags) |

### Key Architecture Facts

- `core` is in **both** `SHARED_APPS` and `TENANT_APPS`.
- `integrations` is in `SHARED_APPS` only, but its URLs are mounted in `tenant_urls.py` at `/integrations/`. Views need `schema_context('public')` to query integrations data from tenant schemas.
- **Billing URLs are at root `/`** in tenant schema, not at `/billing/` (see `tenant_urls.py:12`).
- `integration.apps.IntegrationsConfig` is fully qualified in `INSTALLED_APPS` (others use `'app_name'`).
- `reports` has no migrations directory (static-only or view-only app).

## Routing

- Tenant requests: `tenant_urls.py` — billing at `/`, contracts at `/contracts/`, accounting at `/accounting/`, notifications at `/notifications/`, reports at `/reports/`, API at `/api/v1/`
- Public requests: `urls.py` — landing at `/`, admin at `/admin/`, JWT endpoints at `/api/v1/auth/`
- Language switching: `set_language` view (default `ar`, timezone `Asia/Riyadh`)

## Tenancy

- `TENANT_MODEL = 'tenants.Tenant'`, `TENANT_DOMAIN_MODEL = 'tenants.Domain'`
- `auto_create_schema = False` on Tenant — schema creation is manual in custom `save()` override
- Bootstrap (superuser + subscription types) runs inside `save()` AFTER `create_schema()`
- Feature flags in `core/middleware.py` based on `plan.tier` (basic/pro/enterprise)
- Database engine: `django_tenants.postgresql_backend`; router: `TenantSyncRouter`
- Middleware order: `TenantDebugMiddleware` → `TenantMainMiddleware` → `CorsMiddleware` → ...

## Templates

- All templates in `templates/` directory (not app-level), uses `bootstrap4` form tags
- Context processors: `billing.context_processors.language_context`, `core.context_processors.dashboard_stats`

## Celery

- Broker/backend: Redis (configurable via `REDIS_URL` env)
- Beat schedule: mark_overdue_invoices (1am), send_payment_reminders (9am)
- **Critical**: Celery tasks must use `schema_context(schema_name)` to operate on the correct tenant schema

## REST API (`/api/v1/`)

- JWT auth via SimpleJWT (TokenObtainPairView + TokenRefreshView)
- Pagination: PageNumberPagination, page_size=50
- Filter backends: DjangoFilterBackend, SearchFilter, OrderingFilter
- CORS: all origins when `DEBUG=True`, else from `CORS_ALLOWED_ORIGINS` env

## Setup Prerequisites

1. PostgreSQL running with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` in `.env`
2. Redis running for Celery (optional if `CELERY_ALWAYS_EAGER=True`)
3. Stripe keys (optional for dev) — `.env` has placeholder values
4. Run `seed_plans` then `seed_integrations` after first `migrate_schemas --shared`
