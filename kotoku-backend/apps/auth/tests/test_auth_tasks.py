from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import DeviceSession, User
from apps.auth.tasks import cleanup_expired_device_sessions


def _make_user(phone):
    return User.objects.create_user(phone=phone)


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
