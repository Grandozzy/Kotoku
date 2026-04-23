import logging
import secrets

from django.core.cache import cache

from apps.accounts.models import Account, User
from apps.audit.services import AuditService
from common.exceptions import DomainError

logger = logging.getLogger(__name__)

_OTP_LENGTH = 8
_OTP_TTL_SECONDS = 600
_RATE_LIMIT_TTL_SECONDS = 60


class AuthService:
    @staticmethod
    def send_otp(*, phone: str) -> None:
        cache_key = f"auth_otp:{phone}"
        rate_key = f"auth_otp_rate:{phone}"
        if cache.get(rate_key):
            raise DomainError("OTP already sent. Please wait before requesting another.")
        otp_code = "".join(secrets.choice("0123456789") for _ in range(_OTP_LENGTH))
        cache.set(cache_key, otp_code, timeout=_OTP_TTL_SECONDS)
        cache.set(rate_key, True, timeout=_RATE_LIMIT_TTL_SECONDS)
        logger.info("OTP sent to %s", phone)
        AuditService.record_event(
            event_type="auth.otp_sent",
            entity_type="user",
            entity_id=phone,
            metadata={"channel": "sms"},
        )

    @staticmethod
    def verify_otp(*, phone: str, otp_code: str) -> dict:
        cache_key = f"auth_otp:{phone}"
        cached_otp = cache.get(cache_key)
        if cached_otp is None:
            raise DomainError("OTP has expired or was not sent. Please request a new one.")
        if cached_otp != otp_code:
            raise DomainError("Invalid OTP code.")
        cache.delete(cache_key)
        user, created = User.objects.get_or_create(phone=phone)
        if created:
            Account.objects.create(
                user=user,
                email=f"{phone}@kotoku.app",
                phone=phone,
            )
        AuditService.record_event(
            event_type="auth.otp_verified",
            entity_type="user",
            entity_id=str(user.pk),
            metadata={"new_user": created},
        )
        return {"user": user, "is_new": created}
