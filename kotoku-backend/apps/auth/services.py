import logging
import secrets
from datetime import timedelta

import argon2
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, DeviceSession, User, UserPin
from apps.audit.services import AuditService
from apps.notifications.tasks import send_arkesel_otp
from common.exceptions import DomainError
from common.phone_numbers import normalize_phone_to_e164
from infrastructure.sms.arkesel_client import ArkeselOtpClient

logger = logging.getLogger(__name__)

# OTP is now managed by Arkesel OTP API — generation, storage, expiry,
# rate limiting, and brute-force protection are handled server-side.

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


def _known_device_fingerprints(user: User) -> set[str]:
    return set(
        DeviceSession.objects.filter(user=user)
        .exclude(device_fingerprint="")
        .values_list("device_fingerprint", flat=True)
    )


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
    def send_otp(*, phone: str) -> None:
        phone = normalize_phone_to_e164(phone)

        send_arkesel_otp.delay(
            number=phone,
            message="Your Kotoku verification code is %otp_code%. Valid for 5 minutes.",
        )

        AuditService.record_event(
            event_type="auth.otp_sent",
            entity_type="user",
            entity_id=phone,
            metadata={"channel": "sms"},
        )

    @staticmethod
    def verify_otp(
        *,
        phone: str,
        otp_code: str,
        client_type: str = DeviceSession.CLIENT_MOBILE,
        device_fingerprint: str = "",
        device_name: str = "",
    ) -> dict:
        phone = normalize_phone_to_e164(phone)

        client = ArkeselOtpClient()
        if not client.verify_otp(number=phone, code=otp_code):
            raise DomainError("Invalid or expired OTP code.")

        user = None
        account = None
        session = None
        raw_token = ""

        with transaction.atomic():
            user, created = User.objects.get_or_create(phone=phone)
            if created:
                account = Account.objects.create(
                    user=user,
                    email=f"{phone}@kotoku.app",
                    phone=phone,
                )
            else:
                try:
                    account = user.account
                except Account.DoesNotExist:
                    account = Account.objects.create(
                        user=user,
                        email=f"{phone}@kotoku.app",
                        phone=phone,
                    )
                else:
                    if account.phone != user.phone:
                        account.phone = user.phone
                        account.save(update_fields=["phone", "updated_at"])

            # New device login revokes all other sessions.
            revoked = _revoke_all_sessions(user, reason=DeviceSession.REVOKE_NEW_DEVICE)
            if revoked > 0:
                logger.info(
                    "Revoked %d sessions for %s on new-device OTP login",
                    revoked,
                    phone,
                )

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

        result = _build_token_response(user, session, raw_token)
        result["user"] = user
        result["account"] = account
        return result


def extract_otp_from_message(body: str) -> str | None:
    """Extract a 4-digit OTP from a message body.

    Kept for backward compatibility — OTP is now managed by Arkesel.
    """
    import re
    match = re.search(r"(\d{4})", body)
    if not match:
        return None
    return match.group(1)


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

        if session.client_type != client_type:
            raise DomainError("Refresh token client type mismatch.")

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
    def revoke_raw_token(
        *,
        raw_token: str,
        reason: str = DeviceSession.REVOKE_LOGOUT,
    ) -> None:
        session_id, secret = _split_opaque_token(raw_token)
        try:
            session = DeviceSession.objects.select_for_update().get(
                id=session_id, is_revoked=False
            )
        except DeviceSession.DoesNotExist:
            return
        if check_password(secret, session.refresh_token_hash):
            session.is_revoked = True
            session.revoked_at = timezone.now()
            session.revoked_reason = reason
            session.save(update_fields=["is_revoked", "revoked_at", "revoked_reason"])

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
        phone = normalize_phone_to_e164(phone)
        try:
            user = User.objects.get(phone=phone, is_active=True)
        except User.DoesNotExist:
            raise DomainError("No account found for this phone number.") from None

        known_fingerprints = _known_device_fingerprints(user)
        if known_fingerprints and (
            not device_fingerprint or device_fingerprint not in known_fingerprints
        ):
            AuditService.record_event(
                event_type="auth.pin_force_otp_unknown_device",
                entity_type="user",
                entity_id=str(user.pk),
                metadata={"known_device_count": len(known_fingerprints)},
            )
            raise DomainError("__force_otp__") from None

        try:
            user_pin = UserPin.objects.select_for_update().get(user=user)
        except UserPin.DoesNotExist:
            raise DomainError("PIN not configured. Please sign in with OTP.") from None

        if user_pin.is_locked:
            raise DomainError(
                "Too many failed attempts. Try again after "
                f"{user_pin.locked_until.strftime('%H:%M UTC')}."
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
