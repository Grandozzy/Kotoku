from django.http import JsonResponse
from django.urls import include, path


def root(_: object) -> JsonResponse:
    return JsonResponse({"service": "kotoku-backend", "status": "ok"})


urlpatterns = [
    path("", root, name="root"),
    path("api/accounts/", include("apps.accounts.api.urls")),
    path("api/auth/", include("apps.auth.api.urls")),
    path("api/agreements/", include("apps.agreements.api.urls")),
    path("api/health/", include("apps.health.api.urls")),
    path("api/templates/", include("apps.templates.api.urls")),
]
