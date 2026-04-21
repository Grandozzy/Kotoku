import logging

from celery import shared_task
from django.utils import timezone

from apps.audit.services import AuditService
from apps.notifications.models import Notification
from apps.notifications.providers.sms_provider import SmsNotificationProvider

logger = logging.getLogger(__name__)


@shared_task
def dispatch_notification(notification_id: int) -> None:
    try:
        notification = Notification.objects.select_related("account").get(
            pk=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning("Notification %s not found", notification_id)
        return

    if notification.channel == Notification.Channel.SMS:
        provider = SmsNotificationProvider()
    else:
        logger.warning("No provider for channel %s", notification.channel)
        return

    to = notification.account.phone or notification.account.email
    try:
        success = provider.send(to=to, body=notification.body)
        notification.status = (
            Notification.Status.SENT if success else Notification.Status.FAILED
        )
        if success:
            notification.sent_at = timezone.now()
    except Exception:
        logger.exception("Failed to dispatch notification %s", notification.pk)
        notification.status = Notification.Status.FAILED

    notification.save(update_fields=["status", "sent_at"])
    AuditService.record_event(
        event_type="notification.dispatched",
        entity_type="notification",
        entity_id=str(notification.pk),
        metadata={"status": notification.status},
    )
