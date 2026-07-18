import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "unsafe-dev-key-change-before-production-min-32-bytes",
)
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
    "anymail",
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
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middleware.RequestIdMiddleware",
    "common.middleware.ProbeShieldMiddleware",
    "common.middleware.FirstPartyCorsMiddleware",
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
    "DEFAULT_THROTTLE_RATES": {
        "auth_ip": os.getenv("THROTTLE_AUTH_IP_RATE", "60/h"),
        "refresh_ip": os.getenv("THROTTLE_REFRESH_IP_RATE", "120/h"),
        "send_otp_phone": os.getenv("THROTTLE_SEND_OTP_PHONE_RATE", "3/h"),
        "verify_otp_phone": os.getenv("THROTTLE_VERIFY_OTP_PHONE_RATE", "20/h"),
        "pin_verify_phone": os.getenv("THROTTLE_PIN_VERIFY_PHONE_RATE", "30/h"),
    },
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
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
CELERY_TASK_ALWAYS_EAGER = False
BILLING_ENFORCEMENT_FAIL_OPEN = (
    os.getenv("BILLING_ENFORCEMENT_FAIL_OPEN", "false").lower() == "true"
)
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
    "expire-lapsed-subscriptions": {
        "task": "apps.payments.tasks.expire_lapsed_subscriptions",
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
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "").strip()
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "kotoku-evidence")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "eu-west-1")
AWS_ENDPOINT_URL_S3 = (
    os.getenv("AWS_ENDPOINT_URL_S3", "").strip()
    or os.getenv("AWS_S3_ENDPOINT_URL", "").strip()
)

# --- Infobip (primary SMS provider) ---
INFOBIP_API_KEY = os.getenv("INFOBIP_API_KEY", "")
INFOBIP_BASE_URL = os.getenv("INFOBIP_BASE_URL", "")  # e.g. https://xxxxx.api.infobip.com
INFOBIP_SMS_SENDER = os.getenv("INFOBIP_SMS_SENDER", "")
INFOBIP_WHATSAPP_NUMBER = os.getenv("INFOBIP_WHATSAPP_NUMBER", "")
INFOBIP_WHATSAPP_TEMPLATE_NAME = os.getenv("INFOBIP_WHATSAPP_TEMPLATE_NAME", "")
INFOBIP_SMS_TIMEOUT_SECONDS = int(os.getenv("INFOBIP_SMS_TIMEOUT_SECONDS", "30"))
INFOBIP_WEBHOOK_SECRET = os.getenv("INFOBIP_WEBHOOK_SECRET", "")

# --- Africa's Talking (cold standby — set SMS_BACKEND=africastalking to re-enable) ---
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
SMS_BACKEND = os.getenv("SMS_BACKEND", "arkesel")

# Arkesel OTP API (primary OTP provider)
ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY", "").strip()
ARKESEL_SMS_URL = os.getenv("ARKESEL_SMS_URL", "https://sms.arkesel.com/api/v2/otp").strip()
ARKESEL_SENDER_ID = os.getenv("ARKESEL_SENDER_ID", "").strip()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET", "")

KOTOKU_WEB_URL = os.getenv("KOTOKU_WEB_URL", "https://www.kotoku-app.com").rstrip("/")
CONSENT_LINK_MAX_AGE_SECONDS = int(os.getenv("CONSENT_LINK_MAX_AGE_SECONDS", "604800"))
SEALED_RECEIPT_LINK_MAX_AGE_SECONDS = int(
    os.getenv("SEALED_RECEIPT_LINK_MAX_AGE_SECONDS", "2592000")
)
PAYSTACK_PLAN_CODE_ENV_MAP: dict[str, str] = {
    "personal_basic": "PAYSTACK_PLAN_CODE_PERSONAL_BASIC",
    "personal_plus": "PAYSTACK_PLAN_CODE_PERSONAL_PLUS",
    "personal_protect": "PAYSTACK_PLAN_CODE_PERSONAL_PROTECT",
    "enterprise_standard": "PAYSTACK_PLAN_CODE_ENTERPRISE_STANDARD",
    "enterprise_plus": "PAYSTACK_PLAN_CODE_ENTERPRISE_PLUS",
}
# Map billing plan IDs → Paystack plan codes.
# Set each via env var after creating plans in the Paystack dashboard.
PAYSTACK_PLAN_CODES: dict[str, str] = {
    plan_id: os.getenv(env_name, "")
    for plan_id, env_name in PAYSTACK_PLAN_CODE_ENV_MAP.items()
}
PAYSTACK_CALLBACK_URL = os.getenv("PAYSTACK_CALLBACK_URL", "")

GOOGLE_VISION_PROJECT_ID = os.getenv("GOOGLE_VISION_PROJECT_ID", "").strip()
GOOGLE_VISION_LOCATION = os.getenv("GOOGLE_VISION_LOCATION", "eu").strip() or "eu"
GOOGLE_VISION_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_VISION_SERVICE_ACCOUNT_JSON", "").strip()
GOOGLE_VISION_TIMEOUT_SECONDS = float(os.getenv("GOOGLE_VISION_TIMEOUT_SECONDS", "20"))

REQUIRED_STORAGE_SETTING_NAMES = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_STORAGE_BUCKET_NAME",
    "AWS_S3_REGION_NAME",
)
REQUIRED_ARKESEL_SETTING_NAMES = ("ARKESEL_API_KEY",)
REQUIRED_INFOBIP_SETTING_NAMES = ("INFOBIP_API_KEY", "INFOBIP_BASE_URL")
REQUIRED_PAYMENT_SETTING_NAMES = (
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "PAYSTACK_WEBHOOK_SECRET",
    "PAYSTACK_CALLBACK_URL",
)
STRICT_RUNTIME_VALIDATION = False

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,https://kotoku-app.com,https://www.kotoku-app.com,https://api.kotoku-app.com",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

AUTH_REFRESH_COOKIE_NAME = os.getenv("AUTH_REFRESH_COOKIE_NAME", "kotoku_refresh")
AUTH_REFRESH_COOKIE_DOMAIN = os.getenv("AUTH_REFRESH_COOKIE_DOMAIN", "")
AUTH_REFRESH_COOKIE_PATH = os.getenv("AUTH_REFRESH_COOKIE_PATH", "/api/auth/")
AUTH_REFRESH_COOKIE_SAMESITE = os.getenv("AUTH_REFRESH_COOKIE_SAMESITE", "Lax")
AUTH_REFRESH_COOKIE_SECURE = os.getenv(
    "AUTH_REFRESH_COOKIE_SECURE",
    "false" if DEBUG else "true",
).lower() == "true"
AUTH_WEB_REFRESH_COOKIE_MAX_AGE = int(os.getenv("AUTH_WEB_REFRESH_COOKIE_MAX_AGE", "28800"))
EVIDENCE_VIEW_URL_TTL_SECONDS = int(os.getenv("EVIDENCE_VIEW_URL_TTL_SECONDS", "900"))
_default_email_backend = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "anymail.backends.resend.EmailBackend"
)
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", _default_email_backend)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@kotoku-app.com")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
ANYMAIL = {
    "RESEND_API_KEY": os.getenv("RESEND_API_KEY", ""),
}

_admin_url_path = os.getenv("DJANGO_ADMIN_PATH", "admin/")
ADMIN_URL_PATH = _admin_url_path if _admin_url_path.endswith("/") else f"{_admin_url_path}/"
ADMIN_MFA_CODE_TTL_SECONDS = int(os.getenv("ADMIN_MFA_CODE_TTL_SECONDS", "600"))
ADMIN_SESSION_TIMEOUT_SECONDS = int(os.getenv("ADMIN_SESSION_TIMEOUT_SECONDS", "3600"))
ADMIN_LOGIN_MAX_ATTEMPTS = int(os.getenv("ADMIN_LOGIN_MAX_ATTEMPTS", "10"))
ADMIN_LOGIN_WINDOW_SECONDS = int(os.getenv("ADMIN_LOGIN_WINDOW_SECONDS", "900"))
ADMIN_MFA_MAX_ATTEMPTS_PER_IP = int(os.getenv("ADMIN_MFA_MAX_ATTEMPTS_PER_IP", "10"))
ADMIN_MFA_MAX_ATTEMPTS_PER_USER = int(os.getenv("ADMIN_MFA_MAX_ATTEMPTS_PER_USER", "5"))
ADMIN_MFA_WINDOW_SECONDS = int(os.getenv("ADMIN_MFA_WINDOW_SECONDS", "900"))

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
        # Suppress framework-generated 401/404 probe noise in production logs.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "level": "ERROR",
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
