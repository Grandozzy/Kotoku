from django.db import models

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
