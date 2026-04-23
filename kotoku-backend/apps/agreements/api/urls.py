from django.urls import path

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
]
