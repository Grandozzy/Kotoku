import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_device_sessions() -> dict:
    from apps.accounts.models import DeviceSession  # noqa: PLC0415

    deleted, _ = DeviceSession.objects.filter(
        expires_at__lt=timezone.now(), is_revoked=True
    ).delete()
    logger.info("cleanup_expired_device_sessions: deleted %d rows", deleted)
    return {"deleted": deleted}
