import pytest
from unittest.mock import patch

from apps.accounts.models import Account, User
from apps.notifications.models import Notification
from apps.notifications.tasks import dispatch_notification


def _make_notification(channel=Notification.Channel.SMS):
    user = User.objects.create_user(phone="+233560001001")
    account = Account.objects.create(user=user, email="notif@test.com", phone="+233560001001")
    return Notification.objects.create(
        account=account,
        channel=channel,
        body="Test message",
        status=Notification.Status.PENDING,
    )


@pytest.mark.django_db
class TestDispatchNotification:
    def test_skips_missing_notification(self):
        # Should not raise
        dispatch_notification(99999)

    def test_skips_unsupported_channel(self):
        notif = _make_notification(channel=Notification.Channel.IN_APP)
        dispatch_notification(notif.pk)
        # Task returns early — status remains PENDING
        notif.refresh_from_db()
        assert notif.status == Notification.Status.PENDING

    def test_marks_failed_on_provider_exception(self):
        notif = _make_notification(channel=Notification.Channel.SMS)
        with patch(
            "apps.notifications.providers.sms_provider.SmsNotificationProvider.send",
            side_effect=Exception("SMS gateway down"),
        ):
            dispatch_notification(notif.pk)
        notif.refresh_from_db()
        assert notif.status == Notification.Status.FAILED
