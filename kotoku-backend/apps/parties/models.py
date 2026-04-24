from django.db import models

from apps.agreements.models import Agreement
from apps.identity.models import IdentityRecord


class Party(models.Model):
    class Role(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"
        LANDLORD = "landlord", "Landlord"
        TENANT = "tenant", "Tenant"
        WITNESS = "witness", "Witness"

    class IdType(models.TextChoices):
        GHANA_CARD = "ghana_card", "Ghana Card"
        PASSPORT = "passport", "Passport"
        OTHER = "other", "Other"

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="parties",
    )
    # Linked once the counterparty authenticates; null when created via Parties API.
    identity = models.ForeignKey(
        IdentityRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parties",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    display_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    id_type = models.CharField(max_length=20, choices=IdType.choices, blank=True)
    id_number = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agreement", "role"],
                name="unique_role_per_agreement",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.role})"
