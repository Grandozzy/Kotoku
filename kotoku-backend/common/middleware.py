"""Common middleware for Kotoku.

RequestIdMiddleware
  Reads X-Request-ID from incoming headers (or generates a new UUID) and
  stores it in thread-local state so JsonFormatter can attach it to every
  log line produced during that request. The ID is also echoed back in the
  response header so clients can correlate their own logs.
"""
import uuid

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
