from django.urls import path

from .views import VaultCollectionView, VaultDetailView, VaultExportView

urlpatterns = [
    path("", VaultCollectionView.as_view(), name="vault-collection"),
    path("<int:agreement_id>/", VaultDetailView.as_view(), name="vault-detail"),
    path("<int:agreement_id>/export/", VaultExportView.as_view(), name="vault-export"),
]
