from rest_framework.response import Response


def ok(payload: dict, status_code: int = 200) -> Response:
    return Response({"status": "ok", "data": payload}, status=status_code)
