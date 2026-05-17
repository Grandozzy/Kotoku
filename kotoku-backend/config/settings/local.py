from .base import *  # noqa: F403

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

AWS_ENDPOINT_URL_S3 = os.getenv("AWS_ENDPOINT_URL_S3", "http://minio:9000")  # noqa: F405
AWS_S3_EXTERNAL_URL = os.getenv("AWS_S3_EXTERNAL_URL", "")  # noqa: F405


# Don't override ALLOWED_HOSTS - let base.py handle it from DJANGO_ALLOWED_HOSTS env