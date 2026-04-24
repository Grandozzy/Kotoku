from django.urls import include, path

from .views import (
    AgreementCollectionView,
    AgreementDetailView,
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
]
