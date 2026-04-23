from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.exceptions import DomainError


def kotoku_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(
            {"status": "error", "message": str(exc)},
            status=400,
        )
    return exception_handler(exc, context)
