from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "kotoku-test-secret-key-minimum-32-bytes-2026"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES["default"] = {  # type: ignore[index]
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}
CELERY_TASK_ALWAYS_EAGER = True

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

STATIC_ROOT = BASE_DIR / "output" / "static-test"  # type: ignore[name-defined]
STATIC_ROOT.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {"kotoku": {"handlers": ["null"], "level": "CRITICAL", "propagate": False}},
}
