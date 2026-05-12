import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key-change-me')
DEBUG = config('DEBUG', cast=bool, default=False)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='localhost,127.0.0.1,.localhost')
if DEBUG:
    ALLOWED_HOSTS.append('*')

# Application definition

SHARED_APPS = [
    'django_tenants',
    'tenants',
    'djstripe',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'bootstrap4',
    'rest_framework_simplejwt',
]

TENANT_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'main.apps.MainConfig',
    'billing.apps.BillingConfig',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'bootstrap4',
    'core',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    'core.debug_middleware.TenantDebugMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.FeatureFlagMiddleware',
]

ROOT_URLCONF = 'elem.urls'
PUBLIC_SCHEMA_URLCONF = 'elem.urls'
TENANT_URLCONF = 'elem.tenant_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'billing.context_processors.language_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'elem.wsgi.application'

# Database
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

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

TENANT_MODEL = 'tenants.Tenant'
TENANT_DOMAIN_MODEL = 'tenants.Domain'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('ar', 'Arabic'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static & Media files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'index'

# Stripe
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')
DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:8000', cast=Csv())


# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_TIMEZONE = 'Asia/Riyadh'
CELERY_TASK_ALWAYS_EAGER = config('CELERY_ALWAYS_EAGER', cast=bool, default=False)

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'check-overdue-invoices': {
        'task': 'billing.tasks.mark_overdue_invoices',
        'schedule': crontab(hour=1, minute=0),
    },
    'send-payment-reminders': {
        'task': 'billing.tasks.send_payment_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
}

# Logging
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
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{tenant_schema}] {module} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'billing.api': {'handlers': ['file'], 'level': 'INFO'},
        'billing.services': {'handlers': ['file'], 'level': 'WARNING'},
        'tenants': {'handlers': ['file'], 'level': 'INFO'},
    },
}
