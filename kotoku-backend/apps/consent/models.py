from django.db import models

from apps.agreements.models import Agreement
from apps.parties.models import Party


class ConsentRecord(models.Model):
    class Channel(models.TextChoices):
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Purpose(models.TextChoices):
        CONSENT = "consent", "Initial Consent"
        REOPEN = "reopen_consent", "Reopen Consent"

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    party = models.ForeignKey(
        Party,
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.CONSENT,
        db_index=True,
    )
    otp_code_hash = models.CharField(max_length=128)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Consent for {self.party} on {self.agreement}"
