import logging

from celery import shared_task
from django.utils import timezone

from apps.audit.services import AuditService
from apps.notifications.models import Notification
from apps.notifications.providers.email_provider import EmailNotificationProvider
from apps.notifications.providers.sms_provider import SmsNotificationProvider
from infrastructure.sms.arkesel_client import ArkeselOtpClient

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
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
        to = notification.account.phone or notification.account.email
    elif notification.channel == Notification.Channel.EMAIL:
        provider = EmailNotificationProvider()
        to = notification.account.email
    else:
        logger.warning("No provider for channel %s", notification.channel)
        return

    try:
        if notification.channel == Notification.Channel.EMAIL:
            success = provider.send(to=to, body=notification.body, subject=notification.subject)
        else:
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


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_sms_message(*, to: str, body: str) -> None:
    provider = SmsNotificationProvider()
    success = provider.send(to=to, body=body)
    if not success:
        raise RuntimeError(f"SMS delivery failed for {to}")


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_arkesel_otp(*, number: str, message: str, expiry: int = 5, length: int = 6) -> None:
    """Send OTP via Arkesel OTP API. Arkesel generates and delivers the code."""
    client = ArkeselOtpClient()
    success = client.send_otp(number=number, message=message, expiry=expiry, length=length)
    if not success:
        raise RuntimeError(f"Arkesel OTP send failed for {number}")
