from django.db import models

from apps.accounts.models import Account
from apps.agreements.domain.enums import AgreementStatus


class Agreement(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in AgreementStatus],
        default=AgreementStatus.DRAFT,
        db_index=True,
    )
    scenario_template = models.CharField(max_length=128, blank=True)
    created_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="created_agreements",
    )
    sealed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"
