from django.urls import include, path

from .views import (
    AgreementCollectionView,
    AgreementDetailView,
    SealView,
    ValidateView,
)

urlpatterns = [
    path("", AgreementCollectionView.as_view(), name="agreement-collection"),
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
]
