from django.db import models

from apps.agreements.models import Agreement
from apps.parties.models import Party


class ConsentRecord(models.Model):
    CHANNEL_CHOICES = [
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
    ]

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
    otp_code = models.CharField(max_length=6)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Consent for {self.party} on {self.agreement}"
