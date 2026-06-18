from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.exceptions import DomainError, ServiceUnavailableError


def kotoku_exception_handler(exc, context):
    if isinstance(exc, ServiceUnavailableError):
        payload = {"status": "error", "message": str(exc)}
        if exc.code:
            payload["code"] = exc.code
        return Response(
            payload,
            status=503,
        )
    if isinstance(exc, DomainError):
        payload = {"status": "error", "message": str(exc)}
        if exc.code:
            payload["code"] = exc.code
        return Response(
            payload,
            status=400,
        )
    return exception_handler(exc, context)
