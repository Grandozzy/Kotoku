import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
] + ["healthcheck.railway.app"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "channels",
    "storages",
    "apps.accounts",
    "apps.auth",
    "apps.identity",
    "apps.agreements",
    "apps.parties",
    "apps.evidence",
    "apps.consent",
    "apps.vault",
    "apps.disputes",
    "apps.notifications",
    "apps.audit",
    "apps.health",
    "apps.templates",
    "apps.billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]},
    }
]

DATABASE_URL = os.getenv("DATABASE_URL")
_DB_SSL = os.getenv("DB_SSL_REQUIRE", "false").lower() == "true"
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=60, ssl_require=_DB_SSL),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "kotoku"),
            "USER": os.getenv("DB_USER", "kotoku"),
            "PASSWORD": os.getenv("DB_PASSWORD", "kotoku"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "output" / "static"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.exception_handler.kotoku_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    # Access token lifetime is enforced per client_type in services.py.
    # This default is only used if AccessToken.for_user() is called outside
    # of our token issuance path (e.g. admin tooling).
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    # Refresh tokens are now opaque + DB-backed (DeviceSession).
    # simplejwt's built-in refresh rotation is disabled.
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BEAT_SCHEDULE = {
    "archive-expired-vault-entries": {
        "task": "apps.vault.tasks.archive_expired_vault_entries",
        "schedule": 86400,  # once per day (seconds)
    },
    "recover-stuck-pdf-generating": {
        "task": "apps.vault.tasks.recover_stuck_pdf_generating",
        "schedule": 300,
    },
    "cleanup-stale-drafts": {
        "task": "apps.agreements.tasks.cleanup_stale_drafts",
        "schedule": 86400,
    },
    "cleanup-expired-otp-requests": {
        "task": "apps.auth.tasks.cleanup_expired_otp_requests",
        "schedule": 3600,   # hourly
    },
    "cleanup-expired-device-sessions": {
        "task": "apps.auth.tasks.cleanup_expired_device_sessions",
        "schedule": 86400,  # daily
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0").replace("/0", "/2")],
        },
    },
}

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "kotoku-evidence")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "eu-west-1")

_SMS_USERNAME = os.getenv("SMS_USERNAME", "sandbox")
_SMS_MODE_URL = (
    "https://api.sandbox.africastalking.com/version1/messaging"
    if _SMS_USERNAME == "sandbox"
    else "https://api.africastalking.com/version1/messaging"
)
SMS_API_URL = os.getenv("SMS_API_URL", _SMS_MODE_URL)
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_USERNAME = _SMS_USERNAME
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "")
SMS_BACKEND = os.getenv("SMS_BACKEND", "africastalking")

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

_LOG_FORMAT = os.getenv("LOG_FORMAT", "verbose")  # set LOG_FORMAT=json in production

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {module} {message}",
            "style": "{",
        },
        "json": {
            "()": "common.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": _LOG_FORMAT,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "kotoku.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": _LOG_FORMAT,
        },
    },
    "loggers": {
        "kotoku": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        # Surface Celery task logs through our handler so request IDs carry through.
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()], send_default_pii=False)
