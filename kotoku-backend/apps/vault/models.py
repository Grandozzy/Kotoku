from django.db import models

from apps.agreements.models import Agreement


class VaultEntry(models.Model):
    class ExportStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    agreement = models.OneToOneField(
        Agreement,
        on_delete=models.CASCADE,
        related_name="vault_entry",
    )
    export_status = models.CharField(
        max_length=20,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
        db_index=True,
    )
    pdf_storage_key = models.CharField(max_length=512, blank=True)
    sealed_at = models.DateTimeField(null=True, blank=True)
    retention_until = models.DateTimeField(null=True, blank=True)
    is_free_retention = models.BooleanField(default=True)
    retry_count = models.IntegerField(default=0)
    archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agreement"],
                name="unique_vault_entry_per_agreement",
            ),
        ]

    def __str__(self) -> str:
        return f"Vault: {self.agreement} [{self.export_status}]"
