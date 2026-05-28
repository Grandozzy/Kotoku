from django.conf import settings
from django.core.mail import send_mail

from .base import NotificationProvider


class EmailNotificationProvider(NotificationProvider):
    """
    Sends transactional email via Django's mail backend (anymail/Resend in production,
    console backend in development).
    `to` is the recipient email address.
    `body` is the plain-text message body.
    `subject` is passed separately by the caller; falls back to a generic subject.
    """

    def send(self, to: str, body: str, subject: str = "") -> bool:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@kotoku.app")
        effective_subject = subject or "Kotoku — account notification"
        try:
            send_mail(
                subject=effective_subject,
                message=body,
                from_email=from_email,
                recipient_list=[to],
                fail_silently=False,
            )
            return True
        except Exception:
            return False
