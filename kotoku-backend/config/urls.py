from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path

from apps.accounts.api.views import MeView
from apps.consent.api.views import PublicConsentLinkConfirmView, PublicConsentLinkView
from apps.parties.api.urls import invite_urlpatterns
from apps.vault.api.views import PublicSealedReceiptView


def root(_: object) -> JsonResponse:
    return JsonResponse({"service": "kotoku-backend", "status": "ok"})


def robots(_: object) -> HttpResponse:
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


def favicon(_: object) -> HttpResponse:
    return HttpResponse(status=204)


urlpatterns = [
    path("", root, name="root"),
    path("robots.txt", robots, name="robots-txt"),
    path("favicon.ico", favicon, name="favicon-ico"),
    path(settings.ADMIN_URL_PATH, admin.site.urls),
    path("api/me/", MeView.as_view(), name="me"),
    path("api/accounts/", include("apps.accounts.api.urls")),
    path("api/auth/", include("apps.auth.api.urls")),
    path("api/agreements/", include("apps.agreements.api.urls")),
    path("api/invites/", include((invite_urlpatterns, "invites"))),
    path("api/health/", include("apps.health.api.urls")),
    path("api/templates/", include("apps.templates.api.urls")),
    path("api/vault/", include("apps.vault.api.urls")),
    path("api/disputes/", include("apps.disputes.api.urls")),
    path("api/billing/", include("apps.billing.api.urls")),
    path("api/payments/", include("apps.payments.api.urls")),
    path("api/webhooks/", include("apps.notifications.api.urls")),
    path(
        "api/consent-links/<str:token>/confirm/",
        PublicConsentLinkConfirmView.as_view(),
        name="public-consent-link-confirm",
    ),
    path("api/consent-links/<str:token>/", PublicConsentLinkView.as_view(), name="public-consent-link"),
    path(
        "api/vault-receipts/<str:token>/",
        PublicSealedReceiptView.as_view(),
        name="public-sealed-receipt",
    ),
]
