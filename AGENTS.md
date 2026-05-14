# S-B SaaS Project

## Commands

- Run server: `.\venv\Scripts\python.exe manage.py runserver`
- Create migrations: `.\venv\Scripts\python.exe manage.py makemigrations`
- Apply migrations: `.\venv\Scripts\python.exe manage.py migrate`
- Migrate schemas: `.\venv\Scripts\python.exe manage.py migrate_schemas --shared`
- Create app: `.\venv\Scripts\python.exe manage.py startapp <app_name>`
- Superuser: `.\venv\Scripts\python.exe manage.py createsuperuser`
- Seed plans: `.\venv\Scripts\python.exe manage.py seed_plans`
- Seed integrations: `.\venv\Scripts\python.exe manage.py seed_integrations`
- Run checks: `.\venv\Scripts\python.exe manage.py check`
- Shell: `.\venv\Scripts\python.exe manage.py shell`

## Tech Stack

- Django 6.x + django-tenants (PostgreSQL multi-tenant)
- django-bootstrap4 for UI
- Templates in `templates/` (not app-level)
- DRF 3.17 + SimpleJWT for REST API
- Celery 5.6 + Redis for async tasks
- Stripe + dj-stripe for SaaS billing
- Virtual environment at `venv/`

## Apps (Public Schema)

| App | Description |
|-----|-------------|
| `tenants` | Tenant management, Plan, Domain, Stripe webhooks |
| `core` | Shared middleware, logging, barcode/QR, e-wallet adapters |

## Apps (Tenant Schema)

| App | Description |
|-----|-------------|
| `billing` | Core billing: customers, contracts, meters, invoices, payments, SMS, routes, collectors, e-wallets |
| `accounting` | Double-entry: Chart of Accounts, Journal Entries, AP/AR, Financial Statements |
| `notifications` | Multi-channel: SMS, WhatsApp, Email, Push; templates, providers |
| `integrations` | Third-party integration registry with flexible auth configs |
| `contract_management` | Service contracts with meter readings, recurring invoices, UoM, date ranges |
| `main` | Tenant landing page |

## Key URL Routes

- `/` - Landing/Home
- `/admin/` - Django admin
- `/billing/` - Billing dashboard
- `/accounting/` - Accounting dashboard
- `/notifications/` - Notifications
- `/integrations/` - Integrations
- `/contracts/` - Contracts
- `/api/v1/` - REST API
- `/api/v1/auth/` - JWT auth
- `/stripe/` - Stripe webhooks

## Architecture

- PostgreSQL schema-per-tenant (django-tenants)
- `elem/urls.py` = Public schema routes
- `elem/tenant_urls.py` = Tenant schema routes
- Apps go in `INSTALLED_APPS` as `'app_name.apps.AppNameConfig'`
- Templates use bootstrap4 form tags
- All templates in `templates/` directory (not app-level)