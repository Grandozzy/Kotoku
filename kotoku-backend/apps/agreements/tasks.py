from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.agreements.models import Agreement
from apps.agreements.domain.enums import AgreementStatus


@shared_task
def cleanup_stale_drafts() -> dict:
    """Delete drafts older than 30 days."""
    cutoff = timezone.now() - timedelta(days=30)

    deleted_count, _ = Agreement.objects.filter(
        status=AgreementStatus.DRAFT,
        updated_at__lt=cutoff
    ).delete()

    return {"deleted": deleted_count}