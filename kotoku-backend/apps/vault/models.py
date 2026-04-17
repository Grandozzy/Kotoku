from django.db import models

from apps.agreements.models import Agreement
from apps.evidence.models import EvidenceItem


class VaultEntry(models.Model):
    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="vault_entries",
    )
    evidence_item = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="vault_entries",
    )
    sealed_at = models.DateTimeField(null=True, blank=True)
    pdf_url = models.URLField(blank=True)
    archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Vault: {self.agreement} - {self.evidence_item}"
