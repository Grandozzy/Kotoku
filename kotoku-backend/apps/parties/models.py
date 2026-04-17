from django.db import models

from apps.agreements.models import Agreement
from apps.identity.models import IdentityRecord


class Party(models.Model):
    ROLE_CHOICES = [
        ("buyer", "Buyer"),
        ("seller", "Seller"),
        ("witness", "Witness"),
    ]

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="parties",
    )
    identity = models.ForeignKey(
        IdentityRecord,
        on_delete=models.CASCADE,
        related_name="parties",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    display_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agreement", "identity", "role"],
                name="unique_party_per_agreement_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.role})"
