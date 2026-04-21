import logging

from django.utils import timezone

from apps.accounts.models import Account
from apps.audit.services import AuditService
from apps.notifications.models import Notification
from apps.notifications.providers.sms_provider import SmsNotificationProvider

logger = logging.getLogger(__name__)

_PROVIDERS = {
    Notification.Channel.SMS: SmsNotificationProvider,
}


def _get_provider(channel: str):
    provider_cls = _PROVIDERS.get(channel)
    if provider_cls is None:
        raise ValueError(f"No provider registered for channel: {channel}")
    return provider_cls()


class NotificationService:
    @staticmethod
    def send_notification(
        *,
        account_id: int,
        channel: str,
        body: str,
        destination: str = "",
    ) -> Notification:
        account = Account.objects.get(pk=account_id)
        notification = Notification.objects.create(
            account=account,
            channel=channel,
            body=body,
            status=Notification.Status.PENDING,
        )
        AuditService.record_event(
            event_type="notification.created",
            entity_type="notification",
            entity_id=str(notification.pk),
            metadata={"channel": channel},
        )
        try:
            provider = _get_provider(channel)
            to = destination or account.phone or account.email
            success = provider.send(to=to, body=body)
            notification.status = (
                Notification.Status.SENT if success else Notification.Status.FAILED
            )
            if success:
                notification.sent_at = timezone.now()
        except Exception:
            logger.exception("Failed to dispatch notification %s", notification.pk)
            notification.status = Notification.Status.FAILED
        notification.save(update_fields=["status", "sent_at"])
        return notification
