from django.urls import include, path

from .views import (
    AgreementCollectionView,
    AgreementDetailView,
    PendingActionsView,
    ReopenOtpConfirmView,
    ReopenOtpRequestView,
    ReopenRequestView,
    SealView,
    ValidateView,
)

urlpatterns = [
    path("", AgreementCollectionView.as_view(), name="agreement-collection"),
    path(
        "pending-actions/",
        PendingActionsView.as_view(),
        name="agreement-pending-actions",
    ),
    path(
        "<int:agreement_id>/",
        AgreementDetailView.as_view(),
        name="agreement-detail",
    ),
    path(
        "<int:agreement_id>/parties/",
        include("apps.parties.api.urls"),
    ),
    path(
        "<int:agreement_id>/evidence/",
        include("apps.evidence.api.urls"),
    ),
    path(
        "<int:agreement_id>/consent/",
        include("apps.consent.api.urls"),
    ),
    path(
        "<int:agreement_id>/seal/",
        SealView.as_view(),
        name="agreement-seal",
    ),
    path(
        "<int:agreement_id>/validate/",
        ValidateView.as_view(),
        name="agreement-validate",
    ),
    # Sprint 6: bilateral reopen flow
    path(
        "<int:agreement_id>/reopen-request/",
        ReopenRequestView.as_view(),
        name="agreement-reopen-request",
    ),
    path(
        "<int:agreement_id>/reopen-consent/request-otp/",
        ReopenOtpRequestView.as_view(),
        name="agreement-reopen-otp-request",
    ),
    path(
        "<int:agreement_id>/reopen-consent/confirm/",
        ReopenOtpConfirmView.as_view(),
        name="agreement-reopen-otp-confirm",
    ),
    # Sprint 6: post-seal annotations
    path(
        "<int:agreement_id>/annotations/",
        include("apps.agreements.api.annotations.urls"),
    ),
    # Sprint 6: disputes
    path(
        "<int:agreement_id>/disputes/",
        include("apps.disputes.api.urls"),
    ),
]
