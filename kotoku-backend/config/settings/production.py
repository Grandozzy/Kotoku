import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

_secret_key = os.getenv("DJANGO_SECRET_KEY", "")
if (
    len(_secret_key) < 50
    or _secret_key == "unsafe-dev-key-change-before-production-min-32-bytes"
    or _secret_key.startswith("replace-with")
):
    raise ImproperlyConfigured(
        "Production requires DJANGO_SECRET_KEY to be a strong, random value of at least 50 characters."
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
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
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"  # noqa: F405
AWS_QUERYSTRING_EXPIRY = 3600

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":  # noqa: F405
    options = DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
    options.setdefault("sslmode", "require")
