from .base import *  # noqa: F403

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

AWS_ENDPOINT_URL_S3 = os.getenv("AWS_ENDPOINT_URL_S3", "http://minio:9000")  # noqa: F405
