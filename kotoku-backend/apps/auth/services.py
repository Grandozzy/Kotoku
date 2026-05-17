import logging
import secrets
from datetime import timedelta

import argon2
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, DeviceSession, OTPRequest, User, UserPin
from apps.audit.services import AuditService
from common.exceptions import DomainError
from infrastructure.sms import get_sms_gateway

logger = logging.getLogger(__name__)

_OTP_LENGTH = 8
_OTP_TTL_SECONDS = 600              # 10 minutes
_OTP_MAX_ATTEMPTS = 3               # per OTP record
_OTP_RATE_LIMIT_PER_HOUR = 5

_PIN_LOCK_AFTER = 5                 # failed attempts before 15-min lock
_PIN_FORCE_OTP_AFTER = 10           # total failures before forcing OTP re-auth
_PIN_LOCK_MINUTES = 15

_SESSION_LIFETIME = {
    DeviceSession.CLIENT_MOBILE: timedelta(days=30),
    DeviceSession.CLIENT_WEB: timedelta(hours=8),
}
_ACCESS_TOKEN_LIFETIME = {
    DeviceSession.CLIENT_MOBILE: timedelta(hours=24),
    DeviceSession.CLIENT_WEB: timedelta(hours=2),
}

_SEQUENTIAL_PINS = {
    "0000", "1111", "2222", "3333", "4444",
    "5555", "6666", "7777", "8888", "9999",
    "1234", "2345", "3456", "4567", "5678",
    "6789", "9876", "8765", "7654", "6543",
    "5432", "4321",
}

_ph = argon2.PasswordHasher()


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_opaque_token(session_id: str) -> str:
    """Return a composite opaque refresh token: <session_id>.<random_secret>.

    The session_id prefix lets the server look up the DeviceSession without
    scanning all active sessions for the user.  The random secret (48 bytes
    URL-safe base64 ≈ 64 chars) is what is hashed and stored.
    """
    secret = secrets.token_urlsafe(48)
    return f"{session_id}.{secret}"


def _split_opaque_token(raw_token: str) -> tuple[str, str]:
    """Split '<session_id>.<secret>' → (session_id, secret)."""
    try:
        session_id, secret = raw_token.split(".", 1)
    except ValueError:
        raise DomainError("Invalid refresh token format.") from None
    if not session_id or not secret:
        raise DomainError("Invalid refresh token format.")
    return session_id, secret


def _issue_access_token(user: User, session_id: str, client_type: str) -> str:
    """Issue a short-lived JWT access token with device_session_id claim."""
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=_ACCESS_TOKEN_LIFETIME[client_type])
    token["device_session_id"] = session_id
    token["client_type"] = client_type
    return str(token)


@transaction.atomic
def _create_session(
    *,
    user: User,
    client_type: str,
    device_fingerprint: str = "",
    device_name: str = "",
) -> tuple[DeviceSession, str]:
    """Create a DeviceSession and return (session, raw_refresh_token)."""
    now = timezone.now()
    session = DeviceSession(
        user=user,
        client_type=client_type,
        device_fingerprint=device_fingerprint,
        device_name=device_name,
        expires_at=now + _SESSION_LIFETIME[client_type],
        last_used_at=now,
    )
    raw_token = _make_opaque_token(session.id)
    _, secret = _split_opaque_token(raw_token)
    session.refresh_token_hash = make_password(secret)
    session.save()
    return session, raw_token


def _revoke_all_sessions(user: User, reason: str) -> int:
    now = timezone.now()
    return DeviceSession.objects.filter(
        user=user, is_revoked=False
    ).update(is_revoked=True, revoked_at=now, revoked_reason=reason)


def _build_token_response(user: User, session: DeviceSession, raw_token: str) -> dict:
    access = _issue_access_token(user, session.id, session.client_type)
    try:
        pin_configured = UserPin.objects.filter(user=user).exists()
    except Exception:
        pin_configured = False
    try:
        account_id = user.account.pk
    except Account.DoesNotExist:
        account_id = None
    return {
        "access": access,
        "refresh": raw_token,
        "session_id": session.id,
        "user": {
            "id": user.pk,
            "phone": user.phone,
            "pin_configured": pin_configured,
            "account_id": account_id,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# AuthService — OTP
# ─────────────────────────────────────────────────────────────────────────────

class AuthService:
    @staticmethod
    @transaction.atomic
    def send_otp(*, phone: str) -> None:
        one_hour_ago = timezone.now() - timedelta(hours=1)
        # select_for_update() serializes concurrent send_otp calls for the same
        # phone so the count+create pair is atomic within the transaction.
        recent_count = (
            OTPRequest.objects
            .filter(phone=phone, purpose=OTPRequest.PURPOSE_LOGIN, created_at__gte=one_hour_ago)
            .select_for_update()
            .count()
        )
        if recent_count >= _OTP_RATE_LIMIT_PER_HOUR:
            raise DomainError("Too many OTP requests. Please wait before requesting another.")

        otp_code = "".join(secrets.choice("0123456789") for _ in range(_OTP_LENGTH))
        otp_hash = make_password(otp_code)
        OTPRequest.objects.create(
            phone=phone,
            otp_hash=otp_hash,
            purpose=OTPRequest.PURPOSE_LOGIN,
            expires_at=timezone.now() + timedelta(seconds=_OTP_TTL_SECONDS),
        )

        try:
            get_sms_gateway().send(
                to=phone,
                body=f"Your Kotoku verification code is {otp_code}. Valid for 10 minutes.",
            )
        except Exception:
            logger.exception("Failed to dispatch OTP SMS to %s", phone)

        AuditService.record_event(
            event_type="auth.otp_sent",
            entity_type="user",
            entity_id=phone,
            metadata={"channel": "sms"},
        )

    @staticmethod
    @transaction.atomic
    def verify_otp(
        *,
        phone: str,
        otp_code: str,
        client_type: str = DeviceSession.CLIENT_MOBILE,
        device_fingerprint: str = "",
        device_name: str = "",
    ) -> dict:
        # Find the most recent unused, unexpired login OTP for this phone.
        record = (
            OTPRequest.objects
            .filter(phone=phone, purpose=OTPRequest.PURPOSE_LOGIN, is_used=False)
            .order_by("-created_at")
            .select_for_update()
            .first()
        )
        if record is None or record.is_expired:
            raise DomainError("OTP has expired or was not sent. Please request a new one.")

        record.attempt_count += 1
        if record.attempt_count > _OTP_MAX_ATTEMPTS:
            record.save(update_fields=["attempt_count"])
            raise DomainError("Too many incorrect attempts. Please request a new OTP.")

        if not check_password(otp_code, record.otp_hash):
            record.save(update_fields=["attempt_count"])
            raise DomainError("Invalid OTP code.")

        record.is_used = True
        record.used_at = timezone.now()
        record.save(update_fields=["is_used", "used_at", "attempt_count"])

        user, created = User.objects.get_or_create(phone=phone)
        if created:
            Account.objects.create(
                user=user,
                email=f"{phone}@kotoku.app",
                phone=phone,
            )

        # New device login revokes all other sessions.
        revoked = _revoke_all_sessions(user, reason=DeviceSession.REVOKE_NEW_DEVICE)
        if revoked > 0:
            logger.info("Revoked %d sessions for %s on new-device OTP login", revoked, phone)

        session, raw_token = _create_session(
            user=user,
            client_type=client_type,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
        )

        AuditService.record_event(
            event_type="auth.otp_verified",
            entity_type="user",
            entity_id=str(user.pk),
            metadata={"new_user": created, "session_id": session.id},
        )
        return _build_token_response(user, session, raw_token)


# ─────────────────────────────────────────────────────────────────────────────
# TokenService — refresh rotation
# ─────────────────────────────────────────────────────────────────────────────

class TokenService:
    @staticmethod
    @transaction.atomic
    def refresh(*, raw_token: str, client_type: str) -> dict:
        session_id, secret = _split_opaque_token(raw_token)
        try:
            session = DeviceSession.objects.select_for_update().get(
                id=session_id, is_revoked=False
            )
        except DeviceSession.DoesNotExist:
            raise DomainError("Session not found or revoked.") from None

        if session.is_expired:
            raise DomainError("Session expired. Please sign in again.")

        if not check_password(secret, session.refresh_token_hash):
            raise DomainError("Invalid refresh token.")

        # Rotate: revoke old session, create new one.
        session.is_revoked = True
        session.revoked_at = timezone.now()
        session.revoked_reason = "rotated"
        session.save(update_fields=["is_revoked", "revoked_at", "revoked_reason"])

        user = session.user
        new_session, new_raw_token = _create_session(
            user=user,
            client_type=session.client_type,
            device_fingerprint=session.device_fingerprint,
            device_name=session.device_name,
        )

        AuditService.record_event(
            event_type="auth.token_refreshed",
            entity_type="user",
            entity_id=str(user.pk),
            metadata={"old_session": session_id, "new_session": new_session.id},
        )
        return _build_token_response(user, new_session, new_raw_token)

    @staticmethod
    @transaction.atomic
    def revoke_session(*, session_id: str, reason: str = DeviceSession.REVOKE_LOGOUT) -> None:
        DeviceSession.objects.filter(id=session_id, is_revoked=False).update(
            is_revoked=True,
            revoked_at=timezone.now(),
            revoked_reason=reason,
        )

    @staticmethod
    @transaction.atomic
    def revoke_all_sessions(*, user: User, reason: str = DeviceSession.REVOKE_SIGNOUT_ALL) -> int:
        return _revoke_all_sessions(user, reason)


# ─────────────────────────────────────────────────────────────────────────────
# PinService
# ─────────────────────────────────────────────────────────────────────────────

class PinService:
    @staticmethod
    def validate_strength(pin: str) -> None:
        if not pin.isdigit() or len(pin) != 4:
            raise DomainError("PIN must be exactly 4 digits.")
        if pin in _SEQUENTIAL_PINS:
            raise DomainError("PIN is too simple. Avoid repeated or sequential digits.")

    @staticmethod
    @transaction.atomic
    def setup(*, user: User, pin: str) -> None:
        PinService.validate_strength(pin)
        pin_hash = _ph.hash(pin)
        UserPin.objects.update_or_create(
            user=user,
            defaults={"pin_hash": pin_hash, "failed_attempts": 0, "locked_until": None},
        )
        AuditService.record_event(
            event_type="auth.pin_configured",
            entity_type="user",
            entity_id=str(user.pk),
        )

    @staticmethod
    @transaction.atomic
    def verify(
        *,
        phone: str,
        pin: str,
        client_type: str = DeviceSession.CLIENT_MOBILE,
        device_fingerprint: str = "",
        device_name: str = "",
    ) -> dict:
        try:
            user = User.objects.get(phone=phone, is_active=True)
        except User.DoesNotExist:
            raise DomainError("No account found for this phone number.") from None

        try:
            user_pin = UserPin.objects.select_for_update().get(user=user)
        except UserPin.DoesNotExist:
            raise DomainError("PIN not configured. Please sign in with OTP.") from None

        if user_pin.is_locked:
            raise DomainError(
                f"Too many failed attempts. Try again after {user_pin.locked_until.strftime('%H:%M UTC')}."
            )

        try:
            _ph.verify(user_pin.pin_hash, pin)
        except argon2.exceptions.VerifyMismatchError:
            user_pin.failed_attempts += 1
            if user_pin.failed_attempts >= _PIN_FORCE_OTP_AFTER:
                user_pin.locked_until = None
                user_pin.failed_attempts = 0
                user_pin.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
                AuditService.record_event(
                    event_type="auth.pin_force_otp",
                    entity_type="user",
                    entity_id=str(user.pk),
                )
                raise DomainError("__force_otp__") from None
            if user_pin.failed_attempts >= _PIN_LOCK_AFTER:
                user_pin.locked_until = timezone.now() + timedelta(minutes=_PIN_LOCK_MINUTES)
            user_pin.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
            AuditService.record_event(
                event_type="auth.pin_failed",
                entity_type="user",
                entity_id=str(user.pk),
                metadata={"attempts": user_pin.failed_attempts},
            )
            raise DomainError("Incorrect PIN.") from None

        # Rehash if argon2 params changed.
        if _ph.check_needs_rehash(user_pin.pin_hash):
            user_pin.pin_hash = _ph.hash(pin)
        user_pin.failed_attempts = 0
        user_pin.locked_until = None
        user_pin.save(update_fields=["pin_hash", "failed_attempts", "locked_until", "updated_at"])

        session, raw_token = _create_session(
            user=user,
            client_type=client_type,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
        )

        AuditService.record_event(
            event_type="auth.pin_verified",
            entity_type="user",
            entity_id=str(user.pk),
            metadata={"session_id": session.id},
        )
        return _build_token_response(user, session, raw_token)
