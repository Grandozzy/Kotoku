"""
Phase 7 tests — payment notification delivery.

Verifies that the correct channels (SMS, email, or both) are triggered
for each payment event. Uses the existing Notification model as the
observable — we assert rows are created with the right channel/subject,
rather than asserting on the SMS gateway or email backend directly.

SMS gateway and email backend are patched so nothing hits the network.

Covers:
  - charge.success → SMS + email (subscription activated)
  - invoice.payment_failed → SMS + email
  - expire_lapsed_subscriptions → SMS + email (plan downgraded)
  - subscription.disable → SMS only (cancellation notice)
  - subscription.expiring_cards → SMS only
  - email notification has a non-empty subject
  - account with no email skips email send silently
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from apps.accounts.models import Account, User
from apps.notifications.models import Notification
from apps.payments.models import PaymentEvent, Subscription
from apps.payments.tasks import expire_lapsed_subscriptions, process_payment_event

_seq = 0


def _make_account(plan: str = "personal_basic", email: str = "") -> Account:
    global _seq
    _seq += 1
    phone = f"+233500{_seq:06d}"
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(
        user=user,
        email=email or f"notif{_seq}@test.com",
        phone=phone,
        full_name=f"Test User {_seq}",
        plan=plan,
    )


def _make_sub(account, status=Subscription.STATUS_ACTIVE, sub_id="SUB_notif") -> Subscription:
    return Subscription.objects.create(
        account=account,
        plan_id=account.plan,
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        paystack_sub_id=sub_id,
        paystack_customer_code="CUS_notif",
        status=status,
    )


def _create_event(event_id: str, event_type: str, data: dict) -> PaymentEvent:
    return PaymentEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={"id": event_id, "event": event_type, "data": data},
        processed=False,
    )


def _notifications_for(account) -> list[Notification]:
    return list(Notification.objects.filter(account=account).order_by("channel"))


# Patch the providers so nothing hits the network during tests.
_patch_sms = patch("apps.notifications.providers.sms_provider.SmsNotificationProvider.send", return_value=True)
_patch_email = patch("apps.notifications.providers.email_provider.EmailNotificationProvider.send", return_value=True)


# ── charge.success → SMS + email ─────────────────────────────────────────────


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_charge_success_sends_sms_and_email(mock_email, mock_sms):
    account = _make_account(plan="personal_basic")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        paystack_customer_code="CUS_notif",
        status=Subscription.STATUS_PENDING,
    )

    _create_event("evt_n_charge_001", "charge.success", {
        "plan": {"plan_code": "PLN_plus"},
        "customer": {"customer_code": "CUS_notif", "email": account.email},
        "metadata": {"account_id": account.id, "plan_id": "personal_plus"},
    })

    process_payment_event("evt_n_charge_001")

    notifs = _notifications_for(account)
    channels = {n.channel for n in notifs}
    assert Notification.Channel.SMS in channels
    assert Notification.Channel.EMAIL in channels


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_charge_success_email_has_subject(mock_email, mock_sms):
    account = _make_account(plan="personal_basic")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        paystack_customer_code="CUS_notif2",
        status=Subscription.STATUS_PENDING,
    )

    _create_event("evt_n_charge_002", "charge.success", {
        "plan": {"plan_code": "PLN_plus"},
        "customer": {"customer_code": "CUS_notif2", "email": account.email},
        "metadata": {"account_id": account.id, "plan_id": "personal_plus"},
    })

    process_payment_event("evt_n_charge_002")

    email_notif = Notification.objects.get(account=account, channel=Notification.Channel.EMAIL)
    assert email_notif.subject != ""
    assert "active" in email_notif.subject.lower()


# ── invoice.payment_failed → SMS + email ─────────────────────────────────────


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_invoice_payment_failed_sends_sms_and_email(mock_email, mock_sms):
    account = _make_account(plan="personal_plus")
    _make_sub(account, sub_id="SUB_failnotif")

    _create_event("evt_n_invfail_001", "invoice.payment_failed", {
        "reference": "inv_failnotif_001",
        "amount": 2500,
        "currency": "GHS",
        "subscription": {"subscription_code": "SUB_failnotif"},
    })

    process_payment_event("evt_n_invfail_001")

    channels = {n.channel for n in _notifications_for(account)}
    assert Notification.Channel.SMS in channels
    assert Notification.Channel.EMAIL in channels


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_invoice_payment_failed_email_has_subject(mock_email, mock_sms):
    account = _make_account(plan="personal_plus")
    _make_sub(account, sub_id="SUB_failsubj")

    _create_event("evt_n_invfail_002", "invoice.payment_failed", {
        "reference": "inv_failsubj_001",
        "amount": 2500,
        "currency": "GHS",
        "subscription": {"subscription_code": "SUB_failsubj"},
    })

    process_payment_event("evt_n_invfail_002")

    email_notif = Notification.objects.get(account=account, channel=Notification.Channel.EMAIL)
    assert email_notif.subject != ""
    assert "failed" in email_notif.subject.lower()


# ── expire_lapsed_subscriptions → SMS + email ────────────────────────────────


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_plan_downgraded_sends_sms_and_email(mock_email, mock_sms):
    account = _make_account(plan="personal_plus")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_exp_notif",
        paystack_email=account.email,
        status=Subscription.STATUS_CANCELLED,
        current_period_end=date.today() - timedelta(days=1),
    )

    expire_lapsed_subscriptions()

    channels = {n.channel for n in _notifications_for(account)}
    assert Notification.Channel.SMS in channels
    assert Notification.Channel.EMAIL in channels


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_plan_downgraded_email_has_subject(mock_email, mock_sms):
    account = _make_account(plan="personal_plus")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_exp_subj",
        paystack_email=account.email,
        status=Subscription.STATUS_CANCELLED,
        current_period_end=date.today() - timedelta(days=1),
    )

    expire_lapsed_subscriptions()

    email_notif = Notification.objects.get(account=account, channel=Notification.Channel.EMAIL)
    assert email_notif.subject != ""
    assert "ended" in email_notif.subject.lower()


# ── subscription.disable → SMS only ──────────────────────────────────────────


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_subscription_disable_sends_sms_only(mock_email, mock_sms):
    account = _make_account(plan="personal_plus")
    _make_sub(account, sub_id="SUB_disnotif")

    _create_event("evt_n_disable_001", "subscription.disable", {
        "subscription_code": "SUB_disnotif",
    })

    process_payment_event("evt_n_disable_001")

    channels = {n.channel for n in _notifications_for(account)}
    assert Notification.Channel.SMS in channels
    assert Notification.Channel.EMAIL not in channels


# ── subscription.expiring_cards → SMS only ───────────────────────────────────


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_expiring_cards_sends_sms_only(mock_email, mock_sms):
    account = _make_account(plan="personal_plus")
    _make_sub(account, sub_id="SUB_expcard")

    _create_event("evt_n_expcard_001", "subscription.expiring_cards", {
        "customer": {"email": account.email},
    })

    process_payment_event("evt_n_expcard_001")

    channels = {n.channel for n in _notifications_for(account)}
    assert Notification.Channel.SMS in channels
    assert Notification.Channel.EMAIL not in channels


# ── account with no email skips email silently ────────────────────────────────


@pytest.mark.django_db
@_patch_sms
@_patch_email
def test_charge_success_no_email_address_skips_email(mock_email, mock_sms):
    """An account with an empty email must not raise — email send is skipped."""
    account = _make_account(plan="personal_basic")
    account.email = ""
    account.save(update_fields=["email", "updated_at"])

    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email="fallback@test.com",
        paystack_customer_code="CUS_noemail",
        status=Subscription.STATUS_PENDING,
    )

    _create_event("evt_n_noemail_001", "charge.success", {
        "plan": {"plan_code": "PLN_plus"},
        "customer": {"customer_code": "CUS_noemail", "email": "fallback@test.com"},
        "metadata": {"account_id": account.id, "plan_id": "personal_plus"},
    })

    # Must not raise.
    process_payment_event("evt_n_noemail_001")

    # SMS was still sent.
    assert Notification.objects.filter(account=account, channel=Notification.Channel.SMS).exists()
    # Email was skipped.
    assert not Notification.objects.filter(account=account, channel=Notification.Channel.EMAIL).exists()
