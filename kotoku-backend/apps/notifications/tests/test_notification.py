from unittest.mock import patch

import pytest

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.notifications.tasks import dispatch_notification
from infrastructure.sms.gateway import SmsGateway

_seq = 0


def _account(email="notify@test.com", phone="+233555000111"):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=phone or f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=email, phone=phone)


class TestNotificationService:
    def test_creates_notification_record(self, db):
        account = _account()
        notification = NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.SMS,
            body="Hello from Kotoku",
        )
        assert notification.pk is not None
        assert notification.account_id == account.pk
        assert notification.channel == Notification.Channel.SMS
        assert notification.body == "Hello from Kotoku"

    def test_notification_sent_status_in_stub_mode(self, db):
        account = _account()
        notification = NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.SMS,
            body="Test message",
        )
        assert notification.status == Notification.Status.SENT
        assert notification.sent_at is not None

    def test_emits_audit_event(self, db):
        account = _account()
        NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.SMS,
            body="Audit test",
        )
        assert AuditLog.objects.filter(
            event_type="notification.created",
            entity_type="notification",
        ).exists()

    @patch.object(SmsGateway, "send", return_value=False)
    def test_failed_status_when_provider_fails(self, mock_send, db):
        account = _account()
        notification = NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.SMS,
            body="Will fail",
        )
        assert notification.status == Notification.Status.FAILED
        assert notification.sent_at is None

    @patch.object(SmsGateway, "send", side_effect=Exception("network error"))
    def test_failed_status_on_exception(self, mock_send, db):
        account = _account()
        notification = NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.SMS,
            body="Boom",
        )
        assert notification.status == Notification.Status.FAILED

    def test_raises_on_nonexistent_account(self, db):
        with pytest.raises(Account.DoesNotExist):
            NotificationService.send_notification(
                account_id=99999,
                channel=Notification.Channel.SMS,
                body="Nope",
            )


class TestDispatchTask:
    def test_dispatches_and_updates_status(self, db):
        account = _account()
        notification = Notification.objects.create(
            account=account,
            channel=Notification.Channel.SMS,
            body="Async test",
            status=Notification.Status.PENDING,
        )
        dispatch_notification(notification_id=notification.pk)
        notification.refresh_from_db()
        assert notification.status == Notification.Status.SENT
        assert notification.sent_at is not None

    @patch.object(SmsGateway, "send", return_value=False)
    def test_sets_failed_on_provider_failure(self, mock_send, db):
        account = _account()
        notification = Notification.objects.create(
            account=account,
            channel=Notification.Channel.SMS,
            body="Will fail async",
            status=Notification.Status.PENDING,
        )
        dispatch_notification(notification_id=notification.pk)
        notification.refresh_from_db()
        assert notification.status == Notification.Status.FAILED

    def test_emits_audit_on_dispatch(self, db):
        account = _account()
        notification = Notification.objects.create(
            account=account,
            channel=Notification.Channel.SMS,
            body="Audit async",
            status=Notification.Status.PENDING,
        )
        dispatch_notification(notification_id=notification.pk)
        assert AuditLog.objects.filter(
            event_type="notification.dispatched",
            entity_id=str(notification.pk),
        ).exists()

    def test_noop_on_nonexistent_notification(self, db):
        dispatch_notification(notification_id=99999)


class TestSmsGateway:
    def test_stub_mode_returns_true_when_no_api_key(self, db):
        gateway = SmsGateway()
        assert gateway.send("+233555000111", "Test") is True

    @patch("infrastructure.sms.gateway.urllib.request.urlopen")
    def test_real_mode_returns_true_on_200(self, mock_urlopen, db):
        from django.test import override_settings

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = lambda s, *a: None
        mock_urlopen.return_value.status = 200

        with override_settings(SMS_API_KEY="test-key"):
            gateway = SmsGateway()
            result = gateway.send("+233555000111", "Test")
            assert result is True
            mock_urlopen.assert_called_once()

    @patch("infrastructure.sms.gateway.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_real_mode_returns_false_on_error(self, mock_urlopen, db):
        from django.test import override_settings

        with override_settings(SMS_API_KEY="test-key"):
            gateway = SmsGateway()
            result = gateway.send("+233555000111", "Test")
            assert result is False


class TestSmsNotificationProvider:
    def test_delegates_to_gateway(self, db):
        from apps.notifications.providers.sms_provider import SmsNotificationProvider

        provider = SmsNotificationProvider()
        assert provider.send("+233555000111", "Hello") is True
