import logging

from apps.accounts.models import Account
from apps.audit.services import AuditService
from apps.notifications.models import Notification
from apps.notifications.tasks import dispatch_notification

logger = logging.getLogger(__name__)


class NotificationService:
    _SUPPORTED_CHANNELS = {Notification.Channel.SMS, Notification.Channel.EMAIL}

    @staticmethod
    def send_notification(
        *,
        account_id: int,
        channel: str,
        body: str,
        subject: str = "",
        destination: str = "",
    ) -> Notification:
        if channel not in NotificationService._SUPPORTED_CHANNELS:
            raise ValueError(f"No provider registered for channel: {channel}")

        account = Account.objects.get(pk=account_id)
        notification = Notification.objects.create(
            account=account,
            channel=channel,
            subject=subject,
            body=body,
            status=Notification.Status.PENDING,
        )
        AuditService.record_event(
            event_type="notification.created",
            entity_type="notification",
            entity_id=str(notification.pk),
            metadata={"channel": channel},
        )
        if destination:
            logger.info(
                "Notification %s queued; explicit destination provided but account-bound dispatch will use account contact.",
                notification.pk,
            )
        dispatch_notification.delay(notification.pk)
        return notification
