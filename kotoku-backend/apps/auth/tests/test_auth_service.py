from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Account, DeviceSession, User
from apps.auth.services import AuthService, PinService, extract_otp_from_message
from common.exceptions import DomainError


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestAuthService(TestCase):
    def setUp(self):
        cache.clear()

    def _sent_otp(self, mocked_send):
        body = mocked_send.call_args.kwargs["body"]
        otp = extract_otp_from_message(body)
        assert otp is not None
        return otp

    def test_send_otp_creates_db_request(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None) as mocked_delay:
            AuthService.send_otp(phone="+233501234567")
        otp = self._sent_otp(mocked_delay)
        assert len(otp) == 6
        hourly_count = cache.get("auth_otp_hour:+233501234567")
        assert hourly_count == 1

    def test_send_otp_rate_limited(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None):
            AuthService.send_otp(phone="+233501234567")
            with self.assertRaises(DomainError):
                AuthService.send_otp(phone="+233501234567")

    def test_send_otp_hourly_limit_enforced(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None):
            cache.set("auth_otp_hour:+233501234567", 5, timeout=3600)
            with self.assertRaises(DomainError):
                AuthService.send_otp(phone="+233501234567")

    def test_verify_otp_creates_user_and_account(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None) as mocked_delay:
            AuthService.send_otp(phone="+233501234567")
        otp = self._sent_otp(mocked_delay)
        result = AuthService.verify_otp(phone="+233501234567", otp_code=otp)
        assert result["user"].phone == "+233501234567"
        assert Account.objects.filter(user=result["user"]).exists()

    def test_verify_otp_wrong_code_raises(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None):
            AuthService.send_otp(phone="+233501234567")
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="000000")

    def test_verify_otp_expired_raises(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None):
            AuthService.send_otp(phone="+233501234567")
        from apps.accounts.models import OTPRequest

        OTPRequest.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="123456")

    def test_verify_otp_returns_existing_user(self):
        user = User.objects.create_user(phone="+233501234567")
        Account.objects.create(user=user, email="+233501234567@kotoku.app", phone=user.phone)
        with patch("apps.auth.services.send_sms_message.delay", return_value=None) as mocked_delay:
            AuthService.send_otp(phone="+233501234567")
        otp = self._sent_otp(mocked_delay)
        result = AuthService.verify_otp(phone="+233501234567", otp_code=otp)
        assert result["user"].pk == user.pk
        assert Account.objects.filter(user=result["user"]).count() == 1

    def test_verify_otp_syncs_stale_account_phone_to_verified_user_phone(self):
        user = User.objects.create_user(phone="+233501234568")
        account = Account.objects.create(
            user=user,
            email="+233501234568@kotoku.app",
            phone="0501234568",
        )
        with patch("apps.auth.services.send_sms_message.delay", return_value=None) as mocked_delay:
            AuthService.send_otp(phone="+233501234568")
        otp = self._sent_otp(mocked_delay)
        AuthService.verify_otp(phone="+233501234568", otp_code=otp)
        account.refresh_from_db()
        assert account.phone == user.phone

    def test_verify_otp_locks_after_repeated_failures(self):
        with patch("apps.auth.services.send_sms_message.delay", return_value=None):
            AuthService.send_otp(phone="+233501234567")
        for _ in range(5):
            with self.assertRaises(DomainError):
                AuthService.verify_otp(phone="+233501234567", otp_code="000000")
        from apps.accounts.models import OTPRequest

        record = OTPRequest.objects.get(phone="+233501234567", purpose="login", is_used=False)
        assert record.attempt_count == 5
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="000000")

    def test_pin_verify_forces_otp_on_unknown_device(self):
        user = User.objects.create_user(phone="+233501234567")
        Account.objects.create(user=user, email="+233501234567@kotoku.app", phone=user.phone)
        PinService.setup(user=user, pin="2468")
        DeviceSession.objects.create(
            user=user,
            client_type=DeviceSession.CLIENT_MOBILE,
            expires_at=timezone.now() + timedelta(days=30),
            last_used_at=timezone.now(),
            refresh_token_hash="x",
            device_fingerprint="known-device",
        )
        with self.assertRaises(DomainError) as exc:
            PinService.verify(
                phone="+233501234567",
                pin="2468",
                device_fingerprint="new-device",
            )
        assert str(exc.exception) == "__force_otp__"
