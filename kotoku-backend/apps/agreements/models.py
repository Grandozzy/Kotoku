from django.db import models

from apps.accounts.models import Account


class Agreement(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_CONSENT = "pending_consent", "Pending Consent"
        ACTIVE = "active", "Active"
        SEALED = "sealed", "Sealed"
        REOPEN_REQUESTED = "reopen_requested", "Reopen Requested"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"
        EXPIRED = "expired", "Expired"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    scenario_template = models.CharField(max_length=128, blank=True)
    field_data = models.JSONField(default=dict, blank=True)
    step_index = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="created_agreements",
    )
    sealed_at = models.DateTimeField(null=True, blank=True)
    seal_hash = models.CharField(max_length=64, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"


class Annotation(models.Model):
    """Post-seal note attached to a sealed agreement by one of its parties.

    Annotations do not mutate the agreement or its seal hash; they are purely
    additive. All parties on the agreement can read all annotations.
    """

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    # The party who wrote the annotation (identifies the author within this agreement).
    author_party = models.ForeignKey(
        "parties.Party",
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Annotation on {self.agreement} by {self.author_party}"


class AgreementRevision(models.Model):
    """Snapshot of agreement state at seal time, preserved before reopening."""

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    seal_hash = models.CharField(max_length=64)
    sealed_at = models.DateTimeField()
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("agreement", "revision_number")]
        ordering = ["-revision_number"]

    def __str__(self) -> str:
        return f"Revision {self.revision_number} of {self.agreement}"
