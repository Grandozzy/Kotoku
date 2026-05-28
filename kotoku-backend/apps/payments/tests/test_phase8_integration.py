"""
Phase 8 — end-to-end integration tests.

These tests prove the full pipeline in a single shot rather than testing
the webhook view and the task in isolation. With CELERY_TASK_ALWAYS_EAGER=True
the task runs synchronously inside the same request, so we can assert the
final DB state immediately after the HTTP call.

Covers the specific Phase 8 checklist items not already verified at the
unit level:

  - Valid webhook with charge.success → Account.plan promoted (full pipe)
  - Invalid signature → Account.plan NOT changed (rejection holds end-to-end)
  - Webhook idempotency end-to-end: replayed event does not double-promote
  - subscription.disable via webhook → plan stays until period end (not immediate)
  - expire_lapsed_subscriptions → account downgraded → BillingService blocks seal
    (phase 5 + phase 6 chained)
"""

import hashlib
import hmac
import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Account, User
from apps.agreements.models import Agreement
from apps.billing.services import BillingService
from apps.payments.models import PaymentEvent, Subscription
from apps.payments.tasks import expire_lapsed_subscriptions
from common.exceptions import DomainError

_WEBHOOK_URL = "/api/payments/webhook/"
_WEBHOOK_SECRET = "sk_test_e2esecret"

_seq = 0


def _make_account(plan: str = "personal_basic") -> Account:
    global _seq
    _seq += 1
    phone = f"+233600{_seq:06d}"
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(
        user=user,
        email=f"e2e{_seq}@test.com",
        phone=phone,
        full_name=f"E2E User {_seq}",
        plan=plan,
    )


def _post_webhook(payload: dict, secret: str = _WEBHOOK_SECRET) -> object:
    body = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    client = APIClient()
    return client.post(
        _WEBHOOK_URL,
        data=body,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE=sig,
    )


def _charge_success_payload(account, plan_id: str, event_id: str) -> dict:
    return {
        "id": event_id,
        "event": "charge.success",
        "data": {
            "plan": {"plan_code": f"PLN_{plan_id}"},
            "customer": {
                "customer_code": f"CUS_{account.pk}",
                "email": account.email,
            },
            "metadata": {
                "account_id": account.id,
                "plan_id": plan_id,
            },
        },
    }


# ── Full pipeline: webhook → task → plan promoted ────────────────────────────


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
@patch("apps.payments.tasks._notify")
@patch("apps.payments.tasks._notify_email")
def test_valid_webhook_charge_success_promotes_plan(mock_email, mock_sms):
    """
    POST a valid charge.success webhook → task runs eagerly →
    Account.plan is promoted and Subscription is active.
    """
    account = _make_account(plan="personal_basic")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_personal_plus",
        paystack_email=account.email,
        status=Subscription.STATUS_PENDING,
    )

    resp = _post_webhook(
        _charge_success_payload(account, "personal_plus", "e2e_charge_001")
    )

    assert resp.status_code == 200

    account.refresh_from_db()
    assert account.plan == "personal_plus"

    sub = Subscription.objects.get(account=account)
    assert sub.status == Subscription.STATUS_ACTIVE

    event = PaymentEvent.objects.get(event_id="e2e_charge_001")
    assert event.processed is True
    assert event.error == ""


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_invalid_signature_does_not_promote_plan():
    """
    POST with wrong signature → 400 → Account.plan unchanged.
    """
    account = _make_account(plan="personal_basic")

    body = json.dumps(
        _charge_success_payload(account, "personal_plus", "e2e_badsig_001")
    ).encode()

    client = APIClient()
    resp = client.post(
        _WEBHOOK_URL,
        data=body,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE="wrong_signature",
    )

    assert resp.status_code == 400

    account.refresh_from_db()
    assert account.plan == "personal_basic"
    assert not PaymentEvent.objects.filter(event_id="e2e_badsig_001").exists()


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
@patch("apps.payments.tasks._notify")
@patch("apps.payments.tasks._notify_email")
def test_replayed_webhook_does_not_double_promote(mock_email, mock_sms):
    """
    The same event_id posted twice must be a no-op on the second delivery.
    Account.plan ends up promoted exactly once.
    """
    account = _make_account(plan="personal_basic")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_personal_plus",
        paystack_email=account.email,
        status=Subscription.STATUS_PENDING,
    )

    payload = _charge_success_payload(account, "personal_plus", "e2e_replay_001")

    # First delivery.
    resp1 = _post_webhook(payload)
    assert resp1.status_code == 200

    # Second delivery — same event_id.
    resp2 = _post_webhook(payload)
    assert resp2.status_code == 200

    # Only one PaymentEvent row.
    assert PaymentEvent.objects.filter(event_id="e2e_replay_001").count() == 1

    # Plan was promoted once, not reverted or double-set.
    account.refresh_from_db()
    assert account.plan == "personal_plus"


# ── subscription.disable → plan stays until period end ───────────────────────


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
@patch("apps.payments.tasks._notify")
@patch("apps.payments.tasks._notify_email")
def test_subscription_disable_webhook_plan_not_immediately_downgraded(mock_email, mock_sms):
    """
    subscription.disable → Subscription.status = cancelled, but Account.plan
    must NOT change until expire_lapsed_subscriptions runs after period_end.
    """
    account = _make_account(plan="personal_plus")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_personal_plus",
        paystack_sub_id="SUB_e2e_dis",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
        current_period_end=date.today() + timedelta(days=15),
    )

    payload = {
        "id": "e2e_disable_001",
        "event": "subscription.disable",
        "data": {"subscription_code": "SUB_e2e_dis"},
    }
    resp = _post_webhook(payload)
    assert resp.status_code == 200

    account.refresh_from_db()
    sub = Subscription.objects.get(account=account)

    # Plan still active until period end.
    assert account.plan == "personal_plus"
    assert sub.status == Subscription.STATUS_CANCELLED
    assert sub.cancel_at_period_end is True


# ── expire_lapsed + billing enforcement chained ───────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
@patch("apps.payments.tasks._notify_email")
def test_expired_subscription_downgrade_blocks_seal(mock_email, mock_sms):
    """
    Full chain:
      1. Account on personal_plus (cap = 3).
      2. Subscription expires → expire_lapsed_subscriptions downgrades to personal_basic (cap = 1).
      3. Account has already sealed 1 agreement this month.
      4. BillingService.check_seal_allowed now blocks at the personal_basic cap.
    """
    from django.utils import timezone

    account = _make_account(plan="personal_plus")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_e2e_exp",
        paystack_email=account.email,
        status=Subscription.STATUS_CANCELLED,
        current_period_end=date.today() - timedelta(days=1),
    )

    # Step 2: run the downgrade task.
    expire_lapsed_subscriptions()

    account.refresh_from_db()
    assert account.plan == "personal_basic"

    # Step 3: one seal already consumed this month.
    Agreement.objects.create(
        title="Existing agreement",
        created_by=account,
        status=Agreement.Status.SEALED,
        sealed_at=timezone.now(),
    )

    # Step 4: personal_basic cap = 1 → blocked.
    with pytest.raises(DomainError, match="PLAN_CAP_REACHED"):
        BillingService.check_seal_allowed(account)


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
@patch("apps.payments.tasks._notify_email")
def test_active_subscriber_not_blocked_within_cap(mock_email, mock_sms):
    """
    Account on personal_plus (cap = 3) with an active subscription and
    2 seals consumed must not be blocked.
    """
    from django.utils import timezone

    account = _make_account(plan="personal_plus")
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_e2e_active",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
        current_period_end=date.today() + timedelta(days=15),
    )

    for i in range(2):
        Agreement.objects.create(
            title=f"Agreement {i}",
            created_by=account,
            status=Agreement.Status.SEALED,
            sealed_at=timezone.now(),
        )

    # 2 of 3 used — must not raise.
    BillingService.check_seal_allowed(account)
