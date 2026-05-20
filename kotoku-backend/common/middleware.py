"""Common middleware for Kotoku.

RequestIdMiddleware
  Reads X-Request-ID from incoming headers (or generates a new UUID) and
  stores it in thread-local state so JsonFormatter can attach it to every
  log line produced during that request. The ID is also echoed back in the
  response header so clients can correlate their own logs.
"""
import uuid

from django.conf import settings
from django.http import HttpResponse

from common.logging import clear_request_id, set_request_id


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            clear_request_id()
        response["X-Request-ID"] = request_id
        return response


class FirstPartyCorsMiddleware:
    """Allow credentialed browser API calls only from configured first-party origins."""

    _allowed_methods = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    _allowed_headers = (
        "Authorization, Content-Type, X-Client-Type, X-Device-Fingerprint, "
        "X-Device-Name, X-Request-ID"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        if request.method == "OPTIONS" and origin in settings.CORS_ALLOWED_ORIGINS:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = self._allowed_methods
            response["Access-Control-Allow-Headers"] = self._allowed_headers
            if settings.CORS_ALLOW_CREDENTIALS:
                response["Access-Control-Allow-Credentials"] = "true"
        return response
