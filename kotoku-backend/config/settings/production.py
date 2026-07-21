import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
STRICT_RUNTIME_VALIDATION = True

_secret_key = os.getenv("DJANGO_SECRET_KEY", "")
if (
    len(_secret_key) < 50
    or _secret_key == "unsafe-dev-key-change-before-production-min-32-bytes"
    or _secret_key.startswith("replace-with")
):
    raise ImproperlyConfigured(
        "Production requires DJANGO_SECRET_KEY to be a strong, random value"
        " of at least 50 characters."
    )


def _missing_setting_names(names: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for name in names:
        value = globals().get(name, "")
        if isinstance(value, str):
            if not value.strip():
                missing.append(name)
        elif not value:
            missing.append(name)
    return missing


_missing_runtime_settings = [
    *_missing_setting_names(REQUIRED_STORAGE_SETTING_NAMES),  # noqa: F405
    *_missing_setting_names(REQUIRED_PAYMENT_SETTING_NAMES),  # noqa: F405
]

if SMS_BACKEND == "console":  # noqa: F405
    raise ImproperlyConfigured(
        "Production cannot run with SMS_BACKEND=console because OTPs would be written to logs."
    )
if SMS_BACKEND == "infobip":  # noqa: F405
    _missing_runtime_settings.extend(_missing_setting_names(REQUIRED_INFOBIP_SETTING_NAMES))  # noqa: F405
elif SMS_BACKEND == "arkesel":  # noqa: F405
    _missing_runtime_settings.extend(_missing_setting_names(REQUIRED_ARKESEL_SETTING_NAMES))  # noqa: F405
elif SMS_BACKEND not in ("stub",):  # noqa: F405
    # africastalking standby or any other named backend
    _missing_runtime_settings.extend(_missing_setting_names(REQUIRED_SMS_SETTING_NAMES))  # noqa: F405

for plan_id, env_name in PAYSTACK_PLAN_CODE_ENV_MAP.items():  # noqa: F405
    if not PAYSTACK_PLAN_CODES.get(plan_id, ""):  # noqa: F405
        _missing_runtime_settings.append(env_name)

if _missing_runtime_settings:
    raise ImproperlyConfigured(
        "Production requires the following env vars to be configured: "
        + ", ".join(sorted(set(_missing_runtime_settings)))
    )

# Disable browsable API in production — pure JSON responses only
REST_FRAMEWORK = {
    **globals().get("REST_FRAMEWORK", {}),
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://api.kotoku-app.com,https://kotoku-app.com,https://www.kotoku-app.com",
    ).split(",")
    if origin.strip()
]
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"  # noqa: F405
AWS_QUERYSTRING_EXPIRY = 3600

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":  # noqa: F405
    options = DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
    options.setdefault("sslmode", "require")
