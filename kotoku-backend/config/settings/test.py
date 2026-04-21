from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES["default"] = {  # type: ignore[index]
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}
CELERY_TASK_ALWAYS_EAGER = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {"kotoku": {"handlers": ["null"], "level": "CRITICAL", "propagate": False}},
}
