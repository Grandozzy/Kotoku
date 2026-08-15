from django.db import models
from django.utils import timezone

from apps.accounts.models import Account
from apps.identity.validators import validate_identity_reference


class IdentityRecord(models.Model):
    class VerificationType(models.TextChoices):
        GHANA_CARD = "ghana_card", "Ghana Card"
        PHONE = "phone", "Phone OTP"

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="identities",
    )
    reference = models.CharField(
        max_length=128,
        unique=True,
        validators=[validate_identity_reference],
    )
    verification_type = models.CharField(
        max_length=20,
        choices=VerificationType.choices,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.verification_type}: {self.reference}"


class PartyIdentityVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        MANUAL_REVIEW_REQUIRED = "manual_review_required", "Manual review required"

    party = models.OneToOneField(
        "parties.Party",
        on_delete=models.CASCADE,
        related_name="identity_verification",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    entered_pin = models.CharField(max_length=128, blank=True)
    entered_full_name = models.CharField(max_length=255, blank=True)
    ocr_pin = models.CharField(max_length=128, blank=True)
    ocr_full_name = models.CharField(max_length=255, blank=True)
    front_evidence_id = models.PositiveBigIntegerField(null=True, blank=True)
    back_evidence_id = models.PositiveBigIntegerField(null=True, blank=True)
    selfie_evidence_id = models.PositiveBigIntegerField(null=True, blank=True)
    front_text = models.TextField(blank=True)
    back_text = models.TextField(blank=True)
    face_match_score = models.FloatField(null=True, blank=True)
    failure_codes = models.JSONField(default=list, blank=True)
    detail = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    # Face Liveness fields (populated by the liveness session API flow)
    liveness_session_id = models.CharField(max_length=256, blank=True)
    liveness_status = models.CharField(max_length=16, blank=True)  # "", "pending", "passed", "failed"
    liveness_confidence = models.FloatField(null=True, blank=True)
    liveness_reference_s3_key = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_verified(self, *, detail: str, failure_codes: list[str] | None = None) -> None:
        self.status = self.Status.VERIFIED
        self.detail = detail
        self.failure_codes = failure_codes or []
        self.verified_at = timezone.now()

    def __str__(self) -> str:
        return f"party_identity_verification:{self.party_id}:{self.status}"
