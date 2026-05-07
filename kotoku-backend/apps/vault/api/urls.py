from django.urls import path

from .views import VaultAuditLogView, VaultCollectionView, VaultDetailView, VaultExportView

urlpatterns = [
    path("", VaultCollectionView.as_view(), name="vault-collection"),
    path("<int:agreement_id>/", VaultDetailView.as_view(), name="vault-detail"),
    path("<int:agreement_id>/export/", VaultExportView.as_view(), name="vault-export"),
    path("<int:agreement_id>/audit-log/", VaultAuditLogView.as_view(), name="vault-audit-log"),
]
