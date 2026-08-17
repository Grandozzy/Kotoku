import uuid

from django.db import models
from django.utils import timezone

from apps.agreements.models import Agreement
from apps.identity.models import IdentityRecord

_INVITE_EXPIRY_DAYS = 7


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
        NATIONAL_ID = "national_id", "National ID Card"

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
    id_type = models.CharField(max_length=20, choices=IdType.choices)
    id_number = models.CharField(max_length=128)
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


class PartyInvite(models.Model):
    """One-time token that lets Party B complete their own identity on their device.

    The token is sent via SMS as a deep link. Claiming it requires the authenticated
    account phone to match the party phone — fail-closed per Section 5 of the rules.
    """

    party = models.OneToOneField(
        Party,
        on_delete=models.CASCADE,
        related_name="invite",
    )
    token = models.UUIDField(unique=True, default=uuid.uuid4, db_index=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def is_claimed(self) -> bool:
        return self.accepted_at is not None

    def __str__(self) -> str:
        return f"invite:{self.party_id}:{self.token}"
