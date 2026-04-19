import redis as redis_lib
from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView


def _check_db():
    try:
        connection.ensure_connection()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _check_redis(broker_url):
    try:
        client = redis_lib.Redis.from_url(broker_url)
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        from django.conf import settings

        db_ok, db_msg = _check_db()
        redis_ok, redis_msg = _check_redis(settings.CELERY_BROKER_URL)

        checks = {
            "database": {"status": "ok" if db_ok else "error", "detail": db_msg},
            "redis": {"status": "ok" if redis_ok else "error", "detail": redis_msg},
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

        db_ok, db_msg = _check_db()
        redis_ok, redis_msg = _check_redis(settings.CELERY_BROKER_URL)

        checks = {
            "database": {"status": "ok" if db_ok else "error", "detail": db_msg},
            "redis": {"status": "ok" if redis_ok else "error", "detail": redis_msg},
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
