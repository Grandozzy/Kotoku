from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.agreements.models import Agreement

_DEFAULT_RETENTION_DAYS = 365


class VaultEntry(models.Model):
    class PdfStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    agreement = models.OneToOneField(
        Agreement,
        on_delete=models.CASCADE,
        related_name="vault_entry",
    )
    pdf_url = models.URLField(blank=True)
    pdf_status = models.CharField(
        max_length=12,
        choices=PdfStatus.choices,
        default=PdfStatus.PENDING,
        db_index=True,
    )
    retain_until = models.DateTimeField(null=True, blank=True)
    archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Vault: {self.agreement} [{self.pdf_status}]"

    @classmethod
    def default_retain_until(cls):
        return timezone.now() + timedelta(days=_DEFAULT_RETENTION_DAYS)
