# Django Project

## Commands

- Run server: `.\venv\Scripts\python.exe manage.py runserver`
- Create migrations: `.\venv\Scripts\python.exe manage.py makemigrations`
- Apply migrations: `.\venv\Scripts\python.exe manage.py migrate`
- Create app: `.\venv\Scripts\python.exe manage.py startapp <app_name>`
- Superuser: `.\venv\Scripts\python.exe manage.py createsuperuser`
- Seed accounts: `.\venv\Scripts\python.exe manage.py seed_accounts`
- Seed integrations: `.\venv\Scripts\python.exe manage.py seed_integrations`

## Project Structure

- `settings.py`: Django settings (add apps to INSTALLED_APPS)
- `models.py`: Define database models
- `views.py`: View functions
- `urls.py`: URL routing (include in main urls.py)

## Tech Stack

- Django 6.x with django-bootstrap4
- Templates in `templates/` (not app-level)
- HTMX loaded from CDN
- Virtual environment at `venv/`

## Apps

### Accounting App
- Account, Vendor, Customer
- JournalEntry, JournalLine
- Bill, BillLine (AP)
- Invoice, InvoiceLine (AR)
- Product

### Notifications App
- ChannelProvider (SMS, WhatsApp, Email, Push)
- MessageTemplate with {variable} rendering
- Notification with multi-channel send

### Integrations App
- Integration (provider registry)
- IntegrationConfig with flexible auth (API Key, Basic Auth, Bearer Token, OAuth2, Custom JSON)
- IntegrationLog for API call logging
- Seeded with 16 default providers (Stripe, PayPal, Twilio, SendGrid, etc.)

### Contract Management App
- Contract (meter management, recurring invoices)
- ContractLine (invoice lines)
- MeterReading (track readings)
- DateRange, DateRangeType
- Journal, UoM

## URL Routes

- `/` - Home
- `/accounting/` - Accounting Dashboard
- `/accounting/accounts/` - Chart of accounts
- `/accounting/vendors/` - Vendors
- `/accounting/customers/` - Customers
- `/accounting/bills/` - Bills (AP)
- `/accounting/invoices/` - Invoices (AR)
- `/accounting/ledger/` - General ledger
- `/notifications/` - Notification list
- `/notifications/create/` - Send notification
- `/notifications/templates/` - Message templates
- `/notifications/providers/` - Channel providers
- `/integrations/` - Integration list
- `/integrations/register/` - Register integration
- `/contracts/` - Contracts list
- `/contracts/create/` - Create contract

## Notes

- Apps go in `INSTALLED_APPS` as `'app_name.apps.AppNameConfig'`
- Templates use bootstrap4 form tags
- Login template at `templates/registration/login.html`
- All templates in `templates/` directory (not app-level)