import logging

import redis as redis_lib
from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView

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


def _check_redis(broker_url):
    try:
        client = redis_lib.Redis.from_url(
            broker_url, socket_connect_timeout=_TIMEOUT_SECONDS
        )
        client.ping()
        return True
    except Exception:
        logger.exception("Health check: Redis connection failed")
        return False


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from django.conf import settings

        db_ok = _check_db()
        redis_ok = _check_redis(settings.CELERY_BROKER_URL)

        checks = {
            "database": {"status": "ok" if db_ok else "error"},
            "redis": {"status": "ok" if redis_ok else "error"},
        }
        healthy = db_ok and redis_ok
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
        redis_ok = _check_redis(settings.CELERY_BROKER_URL)

        checks = {
            "database": {"status": "ok" if db_ok else "error"},
            "redis": {"status": "ok" if redis_ok else "error"},
        }
        ready = db_ok and redis_ok
        status_code = 200 if ready else 503
        return Response(
            {
                "status": "ready" if ready else "not_ready",
                "service": "kotoku-backend",
                "checks": checks,
            },
            status=status_code,
        )
