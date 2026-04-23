from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import Account, User
from apps.auth.services import AuthService
from common.exceptions import DomainError


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestAuthService(TestCase):
    def setUp(self):
        cache.clear()

    def test_send_otp_creates_cache_entry(self):
        AuthService.send_otp(phone="+233501234567")
        cached = cache.get("auth_otp:+233501234567")
        assert cached is not None
        assert len(cached) == 8

    def test_send_otp_rate_limited(self):
        AuthService.send_otp(phone="+233501234567")
        with self.assertRaises(DomainError):
            AuthService.send_otp(phone="+233501234567")

    def test_verify_otp_creates_user_and_account(self):
        AuthService.send_otp(phone="+233501234567")
        otp = cache.get("auth_otp:+233501234567")
        result = AuthService.verify_otp(phone="+233501234567", otp_code=otp)
        assert result["user"].phone == "+233501234567"
        assert Account.objects.filter(user=result["user"]).exists()

    def test_verify_otp_wrong_code_raises(self):
        AuthService.send_otp(phone="+233501234567")
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="00000000")

    def test_verify_otp_expired_raises(self):
        AuthService.send_otp(phone="+233501234567")
        cache.delete("auth_otp:+233501234567")
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="12345678")

    def test_verify_otp_returns_existing_user(self):
        user = User.objects.create_user(phone="+233501234567")
        Account.objects.create(user=user, email="+233501234567@kotoku.app", phone=user.phone)
        AuthService.send_otp(phone="+233501234567")
        otp = cache.get("auth_otp:+233501234567")
        result = AuthService.verify_otp(phone="+233501234567", otp_code=otp)
        assert result["user"].pk == user.pk
        assert Account.objects.filter(user=result["user"]).count() == 1
