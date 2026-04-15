from rest_framework.views import APIView

from common.responses import ok


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # type: ignore[override]
        return ok({"service": "kotoku-backend", "status": "healthy"})
