from django.db import models

from apps.agreements.models import Agreement
from apps.parties.models import Party


class EvidenceItem(models.Model):
    FILE_TYPE_CHOICES = [
        ("photo", "Photo"),
        ("voice_note", "Voice Note"),
        ("signature", "Signature"),
        ("document", "Document"),
    ]

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="evidence_items",
    )
    uploaded_by = models.ForeignKey(
        Party,
        on_delete=models.CASCADE,
        related_name="uploaded_evidence",
    )
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_hash = models.CharField(max_length=128)
    storage_url = models.URLField(blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.file_type}: {self.original_name or self.file_hash[:12]}"
