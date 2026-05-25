import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_admin_mfa_email(*, to: str, code: str, ttl_seconds: int) -> None:
    send_mail(
        subject="Your Kotoku admin sign-in code",
        message=(
            f"Your Kotoku admin sign-in code is {code}.\n\n"
            f"It expires in {ttl_seconds // 60} minutes."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )
    logger.info("Admin MFA email dispatched to %s", to)
