import logging

import redis as redis_lib
from botocore.exceptions import BotoCoreError, ClientError
from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView

from infrastructure.storage.s3 import S3StorageClient

logger = logging.getLogger(__name__)


_TIMEOUT_SECONDS = 3


def _check_db():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        logger.exception("Health check: database connection failed")
        return False


def _redis_check_result(broker_url):
    if not broker_url:
        logger.warning("Health check: Redis URL not configured")
        return "skipped"

    try:
        client = redis_lib.Redis.from_url(
            broker_url, socket_connect_timeout=_TIMEOUT_SECONDS
        )
        client.ping()
        return "ok"
    except Exception:
        logger.exception("Health check: Redis connection failed")
        return "error"


def _config_check_result():
    from django.conf import settings

    def _missing(names):
        missing = []
        for name in names:
            value = getattr(settings, name, "")
            if isinstance(value, str):
                if not value.strip():
                    missing.append(name)
            elif not value:
                missing.append(name)
        return missing

    storage_missing = _missing(getattr(settings, "REQUIRED_STORAGE_SETTING_NAMES", ()))
    payment_missing = _missing(getattr(settings, "REQUIRED_PAYMENT_SETTING_NAMES", ()))

    sms_missing = []
    if getattr(settings, "SMS_BACKEND", "") != "stub":
        sms_missing = _missing(getattr(settings, "REQUIRED_SMS_SETTING_NAMES", ()))

    plan_code_missing = []
    for plan_id, env_name in getattr(settings, "PAYSTACK_PLAN_CODE_ENV_MAP", {}).items():
        if not getattr(settings, "PAYSTACK_PLAN_CODES", {}).get(plan_id, "").strip():
            plan_code_missing.append(env_name)

    groups = {
        "storage": storage_missing,
        "payments": payment_missing,
        "sms": sms_missing,
        "paystack_plan_codes": plan_code_missing,
    }
    all_missing = [name for missing in groups.values() for name in missing]
    return {
        "status": "ok" if not all_missing else "error",
        "missing": all_missing,
        "groups": {
            group: {"status": "ok" if not missing else "error", "missing": missing}
            for group, missing in groups.items()
        },
    }


def _storage_check_result(config_check):
    if config_check["groups"]["storage"]["status"] != "ok":
        return {"status": "skipped", "reason": "storage_config_missing"}
    try:
        S3StorageClient().check_bucket_access()
        return {"status": "ok"}
    except (BotoCoreError, ClientError):
        logger.exception("Health check: storage connectivity failed")
        return {"status": "error"}
    except Exception:
        logger.exception("Health check: unexpected storage probe failure")
        return {"status": "error"}


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from django.conf import settings

        db_ok = _check_db()
        redis_status = _redis_check_result(getattr(settings, "CELERY_BROKER_URL", ""))
        config_check = _config_check_result()
        config_ok = config_check["status"] == "ok"
        storage_check = _storage_check_result(config_check)
        storage_ok = storage_check["status"] == "ok"
        strict = getattr(settings, "STRICT_RUNTIME_VALIDATION", False)

        checks = {
            "database": {"status": "ok" if db_ok else "error"},
            "redis": {"status": redis_status},
            "config": config_check,
            "storage": storage_check,
        }
        healthy = db_ok and (config_ok or not strict) and (storage_ok or not strict)
        status_code = 200 if healthy else 503
        return Response(
            {
                "status": "healthy" if healthy else "unhealthy",
                "service": "kotoku-backend",
                "checks": checks,
            },
            status=status_code,
        )


class ReadinessView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from django.conf import settings

        db_ok = _check_db()
        redis_status = _redis_check_result(getattr(settings, "CELERY_BROKER_URL", ""))
        redis_ok = redis_status == "ok"
        config_check = _config_check_result()
        config_ok = config_check["status"] == "ok"
        storage_check = _storage_check_result(config_check)
        storage_ok = storage_check["status"] == "ok"
        strict = getattr(settings, "STRICT_RUNTIME_VALIDATION", False)

        checks = {
            "database": {"status": "ok" if db_ok else "error"},
            "redis": {"status": redis_status},
            "config": config_check,
            "storage": storage_check,
        }
        ready = db_ok and redis_ok and (config_ok or not strict) and (storage_ok or not strict)
        status_code = 200 if ready else 503
        return Response(
            {
                "status": "ready" if ready else "not_ready",
                "service": "kotoku-backend",
                "checks": checks,
            },
            status=status_code,
        )
