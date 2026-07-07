from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import DeviceSession, OTPRequest, User
from apps.auth.tasks import cleanup_expired_device_sessions, cleanup_expired_otp_requests


def _make_user(phone):
    return User.objects.create_user(phone=phone)


def _make_otp(phone, expired=False):
    delta = -timedelta(minutes=5) if expired else timedelta(minutes=5)
    return OTPRequest.objects.create(
        phone=phone,
        otp_hash="x",
        purpose=OTPRequest.PURPOSE_LOGIN,
        expires_at=timezone.now() + delta,
    )


def _make_session(user, expired=False, revoked=False):
    delta = -timedelta(days=1) if expired else timedelta(days=30)
    return DeviceSession.objects.create(
        user=user,
        client_type=DeviceSession.CLIENT_MOBILE,
        expires_at=timezone.now() + delta,
        last_used_at=timezone.now(),
        is_revoked=revoked,
        revoked_at=timezone.now() if revoked else None,
        revoked_reason="logout" if revoked else "",
        refresh_token_hash="x",
    )


@pytest.mark.django_db
class TestCleanupExpiredOtpRequests:
    def test_deletes_expired_records(self):
        _make_otp("+233500001001", expired=True)
        result = cleanup_expired_otp_requests()
        assert result["deleted"] == 1
        assert OTPRequest.objects.count() == 0

    def test_keeps_unexpired_records(self):
        _make_otp("+233500001002", expired=False)
        result = cleanup_expired_otp_requests()
        assert result["deleted"] == 0
        assert OTPRequest.objects.count() == 1

    def test_deletes_only_expired(self):
        _make_otp("+233500001003", expired=True)
        _make_otp("+233500001004", expired=False)
        result = cleanup_expired_otp_requests()
        assert result["deleted"] == 1
        assert OTPRequest.objects.count() == 1

    def test_returns_zero_when_nothing_to_delete(self):
        result = cleanup_expired_otp_requests()
        assert result == {"deleted": 0}


@pytest.mark.django_db
class TestCleanupExpiredDeviceSessions:
    def test_deletes_expired_and_revoked_sessions(self):
        user = _make_user("+233500002001")
        _make_session(user, expired=True, revoked=True)
        result = cleanup_expired_device_sessions()
        assert result["deleted"] == 1
        assert DeviceSession.objects.count() == 0

    def test_keeps_active_sessions(self):
        user = _make_user("+233500002002")
        _make_session(user, expired=False, revoked=False)
        result = cleanup_expired_device_sessions()
        assert result["deleted"] == 0
        assert DeviceSession.objects.count() == 1

    def test_keeps_expired_but_not_revoked(self):
        user = _make_user("+233500002003")
        _make_session(user, expired=True, revoked=False)
        result = cleanup_expired_device_sessions()
        assert result["deleted"] == 0

    def test_keeps_revoked_but_not_expired(self):
        user = _make_user("+233500002004")
        _make_session(user, expired=False, revoked=True)
        result = cleanup_expired_device_sessions()
        assert result["deleted"] == 0

    def test_returns_zero_when_nothing_to_delete(self):
        result = cleanup_expired_device_sessions()
        assert result == {"deleted": 0}
