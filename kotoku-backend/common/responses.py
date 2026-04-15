from rest_framework.response import Response


def ok(payload: dict) -> Response:
    return Response({"status": "ok", "data": payload})
