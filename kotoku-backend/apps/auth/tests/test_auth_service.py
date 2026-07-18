from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Account, DeviceSession, User
from apps.auth.services import AuthService, PinService
from common.exceptions import DomainError


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestAuthService(TestCase):
    def setUp(self):
        cache.clear()

    def test_send_otp_dispatches_to_arkesel(self):
        with patch("apps.auth.services.send_arkesel_otp.delay", return_value=None) as mocked_delay:
            AuthService.send_otp(phone="+233501234567")
        mocked_delay.assert_called_once()
        kwargs = mocked_delay.call_args.kwargs
        assert kwargs["number"] == "+233501234567"
        assert "%otp_code%" in kwargs["message"]

    def test_verify_otp_creates_user_and_account(self):
        with patch(
            "infrastructure.sms.arkesel_client.ArkeselOtpClient.verify_otp",
            return_value=True,
        ):
            result = AuthService.verify_otp(phone="+233501234567", otp_code="123456")
        assert result["user"].phone == "+233501234567"
        assert Account.objects.filter(user=result["user"]).exists()

    def test_verify_otp_wrong_code_raises(self):
        with patch(
            "infrastructure.sms.arkesel_client.ArkeselOtpClient.verify_otp",
            return_value=False,
        ):
            with self.assertRaises(DomainError):
                AuthService.verify_otp(phone="+233501234567", otp_code="000000")

    def test_verify_otp_returns_existing_user(self):
        user = User.objects.create_user(phone="+233501234567")
        Account.objects.create(user=user, email="+233501234567@kotoku.app", phone=user.phone)
        with patch(
            "infrastructure.sms.arkesel_client.ArkeselOtpClient.verify_otp",
            return_value=True,
        ):
            result = AuthService.verify_otp(phone="+233501234567", otp_code="123456")
        assert result["user"].pk == user.pk
        assert Account.objects.filter(user=result["user"]).count() == 1

    def test_verify_otp_syncs_stale_account_phone_to_verified_user_phone(self):
        user = User.objects.create_user(phone="+233501234568")
        account = Account.objects.create(
            user=user,
            email="+233501234568@kotoku.app",
            phone="0501234568",
        )
        with patch(
            "infrastructure.sms.arkesel_client.ArkeselOtpClient.verify_otp",
            return_value=True,
        ):
            AuthService.verify_otp(phone="+233501234568", otp_code="123456")
        account.refresh_from_db()
        assert account.phone == user.phone

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
