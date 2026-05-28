"""
Phase 5 tests — expire_lapsed_subscriptions beat task.

Covers:
  - Cancelled subscription past period_end → account downgraded to personal_basic
  - Past-due subscription past period_end → account downgraded to personal_basic
  - Active subscription → never touched
  - Subscription with no period_end → never touched
  - Already-expired subscription → idempotent, not processed again
  - Account already on personal_basic → plan field not re-saved unnecessarily
  - AuditLog written for each downgrade
  - Notification sent for each downgrade
  - Multiple lapsed subscriptions processed in one run
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.payments.models import Subscription
from apps.payments.tasks import expire_lapsed_subscriptions

_seq = 0


def _make_account(plan: str = "personal_plus") -> Account:
    global _seq
    _seq += 1
    phone = f"+233300{_seq:06d}"
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(
        user=user,
        email=f"exp{_seq}@test.com",
        phone=phone,
        plan=plan,
    )


def _make_sub(account, status, period_end=None) -> Subscription:
    return Subscription.objects.create(
        account=account,
        plan_id=account.plan,
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        paystack_sub_id=f"SUB_{account.pk}",
        status=status,
        current_period_end=period_end,
    )


_YESTERDAY = date.today() - timedelta(days=1)
_TOMORROW = date.today() + timedelta(days=1)


# ── Downgrade cases ───────────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_cancelled_past_period_end_is_downgraded(mock_notify):
    account = _make_account(plan="personal_plus")
    sub = _make_sub(account, Subscription.STATUS_CANCELLED, period_end=_YESTERDAY)

    expire_lapsed_subscriptions()

    account.refresh_from_db()
    sub.refresh_from_db()

    assert account.plan == "personal_basic"
    assert sub.status == Subscription.STATUS_EXPIRED
    assert AuditLog.objects.filter(
        event_type="payment.plan_downgraded",
        entity_type="account",
        entity_id=str(account.pk),
    ).exists()
    mock_notify.assert_called_once()


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_past_due_past_period_end_is_downgraded(mock_notify):
    account = _make_account(plan="personal_protect")
    sub = _make_sub(account, Subscription.STATUS_PAST_DUE, period_end=_YESTERDAY)

    expire_lapsed_subscriptions()

    account.refresh_from_db()
    sub.refresh_from_db()

    assert account.plan == "personal_basic"
    assert sub.status == Subscription.STATUS_EXPIRED
    mock_notify.assert_called_once()


# ── Non-downgrade cases ───────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_active_subscription_never_touched(mock_notify):
    account = _make_account(plan="personal_plus")
    sub = _make_sub(account, Subscription.STATUS_ACTIVE, period_end=_YESTERDAY)

    expire_lapsed_subscriptions()

    account.refresh_from_db()
    sub.refresh_from_db()

    assert account.plan == "personal_plus"
    assert sub.status == Subscription.STATUS_ACTIVE
    mock_notify.assert_not_called()


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_cancelled_future_period_end_not_downgraded(mock_notify):
    account = _make_account(plan="personal_plus")
    sub = _make_sub(account, Subscription.STATUS_CANCELLED, period_end=_TOMORROW)

    expire_lapsed_subscriptions()

    account.refresh_from_db()
    sub.refresh_from_db()

    assert account.plan == "personal_plus"
    assert sub.status == Subscription.STATUS_CANCELLED
    mock_notify.assert_not_called()


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_cancelled_no_period_end_not_downgraded(mock_notify):
    account = _make_account(plan="personal_plus")
    sub = _make_sub(account, Subscription.STATUS_CANCELLED, period_end=None)

    expire_lapsed_subscriptions()

    account.refresh_from_db()
    sub.refresh_from_db()

    assert account.plan == "personal_plus"
    assert sub.status == Subscription.STATUS_CANCELLED
    mock_notify.assert_not_called()


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_already_expired_subscription_is_idempotent(mock_notify):
    """Running the task twice must not double-process an expired subscription."""
    account = _make_account(plan="personal_basic")
    sub = _make_sub(account, Subscription.STATUS_EXPIRED, period_end=_YESTERDAY)

    expire_lapsed_subscriptions()
    expire_lapsed_subscriptions()

    sub.refresh_from_db()
    assert sub.status == Subscription.STATUS_EXPIRED
    mock_notify.assert_not_called()
    assert AuditLog.objects.filter(event_type="payment.plan_downgraded").count() == 0


# ── Edge cases ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_account_already_on_personal_basic_still_expires_sub(mock_notify):
    """
    If the account was already on personal_basic (e.g. manually overridden),
    the subscription should still be marked expired and audit logged.
    """
    account = _make_account(plan="personal_basic")
    sub = _make_sub(account, Subscription.STATUS_CANCELLED, period_end=_YESTERDAY)

    expire_lapsed_subscriptions()

    sub.refresh_from_db()
    assert sub.status == Subscription.STATUS_EXPIRED
    assert AuditLog.objects.filter(event_type="payment.plan_downgraded").exists()


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_multiple_lapsed_subscriptions_all_downgraded(mock_notify):
    accounts = [_make_account(plan="personal_plus") for _ in range(3)]
    subs = [
        _make_sub(a, Subscription.STATUS_CANCELLED, period_end=_YESTERDAY)
        for a in accounts
    ]

    expire_lapsed_subscriptions()

    for account, sub in zip(accounts, subs):
        account.refresh_from_db()
        sub.refresh_from_db()
        assert account.plan == "personal_basic"
        assert sub.status == Subscription.STATUS_EXPIRED

    assert mock_notify.call_count == 3
    assert AuditLog.objects.filter(event_type="payment.plan_downgraded").count() == 3


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_mix_of_lapsed_and_active_only_lapsed_downgraded(mock_notify):
    lapsed_account = _make_account(plan="personal_plus")
    active_account = _make_account(plan="personal_protect")

    _make_sub(lapsed_account, Subscription.STATUS_CANCELLED, period_end=_YESTERDAY)
    _make_sub(active_account, Subscription.STATUS_ACTIVE, period_end=_TOMORROW)

    expire_lapsed_subscriptions()

    lapsed_account.refresh_from_db()
    active_account.refresh_from_db()

    assert lapsed_account.plan == "personal_basic"
    assert active_account.plan == "personal_protect"
    assert mock_notify.call_count == 1
