from django.db import models

from apps.accounts.models import Account
from apps.identity.validators import validate_identity_reference


class IdentityRecord(models.Model):
    VERIFICATION_TYPE_CHOICES = [
        ("ghana_card", "Ghana Card"),
        ("phone", "Phone OTP"),
    ]

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="identities",
    )
    reference = models.CharField(max_length=128, validators=[validate_identity_reference])
    verification_type = models.CharField(
        max_length=20,
        choices=VERIFICATION_TYPE_CHOICES,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.verification_type}: {self.reference}"
