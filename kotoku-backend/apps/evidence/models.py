from django.db import models

from apps.agreements.models import Agreement
from apps.parties.models import Party


class EvidenceItem(models.Model):
    class FileType(models.TextChoices):
        PHOTO = "photo", "Photo"
        VOICE_NOTE = "voice_note", "Voice Note"
        SIGNATURE = "signature", "Signature"
        DOCUMENT = "document", "Document"

    class UploadStatus(models.TextChoices):
        # Presigned URL issued; client has not yet confirmed the upload.
        PENDING = "pending", "Pending"
        # Client confirmed after direct-to-S3 upload, or created via the
        # legacy upload_evidence() path (which streams through Django).
        CONFIRMED = "confirmed", "Confirmed"

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="evidence_items",
    )
    # Null when created via the presigned URL path — linked once we know which
    # authenticated party requested the upload, if a matching party exists.
    uploaded_by = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_evidence",
    )
    # Generic category derived from mime_type (photo / voice_note / document).
    file_type = models.CharField(max_length=20, choices=FileType.choices)
    # Semantic evidence slot: e.g. "vehicle_photo_front", "seller_id_photo".
    evidence_type = models.CharField(max_length=128, blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    # S3 object key — generated at upload-url time, used to verify the
    # confirm step and build the permanent storage URL.
    file_key = models.CharField(max_length=512, blank=True, db_index=True)
    # SHA-256 of the file content.  Empty for presigned uploads (client never
    # streams the bytes through Django).
    file_hash = models.CharField(max_length=128, blank=True)
    storage_url = models.URLField(blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    # Default CONFIRMED so that items created via the legacy upload_evidence()
    # service and items created directly in tests remain valid for can_seal checks.
    upload_status = models.CharField(
        max_length=20,
        choices=UploadStatus.choices,
        default=UploadStatus.CONFIRMED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        label = self.evidence_type or self.file_type
        return f"{label}: {self.original_name or self.file_key or self.file_hash[:12]}"
