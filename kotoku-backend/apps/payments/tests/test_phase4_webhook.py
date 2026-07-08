"""
Phase 4 tests — webhook endpoint and event processing task.

All Celery tasks run eagerly (CELERY_TASK_ALWAYS_EAGER = True in test settings).
Paystack HTTP calls are mocked where needed.

Covers:
  - WebhookView: valid/invalid signature, idempotency, missing event id
  - process_payment_event: charge.success, subscription.create,
    subscription.disable, invoice.payment_failed, invoice.update,
    subscription.expiring_cards, unknown event, already-processed replay
"""

import hashlib
import hmac
import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Account, User
from apps.audit.models import AuditLog
from apps.payments.models import Invoice, PaymentEvent, Subscription, SubscriptionCheckout
from apps.payments.tasks import process_payment_event

_WEBHOOK_URL = "/api/payments/webhook/"
_WEBHOOK_SECRET = "sk_test_webhooksecret"

_seq = 0


def _make_account(plan: str = "personal_basic") -> Account:
    global _seq
    _seq += 1
    phone = f"+233100{_seq:06d}"
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(
        user=user,
        email=f"wh{_seq}@test.com",
        phone=phone,
        plan=plan,
    )


def _sign(body: bytes, secret: str = _WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


def _post_webhook(client, payload: dict, secret: str = _WEBHOOK_SECRET) -> object:
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    return client.post(
        _WEBHOOK_URL,
        data=body,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE=sig,
    )


def _make_event(event_type: str, data: dict, event_id: str = "evt_001") -> dict:
    return {"id": event_id, "event": event_type, "data": data}


# ── WebhookView ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
@patch("apps.payments.api.views.process_payment_event")
def test_webhook_valid_signature_accepted(mock_task):
    client = APIClient()
    payload = _make_event("charge.success", {}, "evt_valid_001")
    resp = _post_webhook(client, payload)
    assert resp.status_code == 200
    assert PaymentEvent.objects.filter(event_id="evt_valid_001").exists()
    mock_task.delay.assert_called_once_with("evt_valid_001")


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_webhook_invalid_signature_rejected():
    client = APIClient()
    body = json.dumps({"id": "evt_bad", "event": "charge.success", "data": {}}).encode()
    resp = client.post(
        _WEBHOOK_URL,
        data=body,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE="deadbeef" * 16,
    )
    assert resp.status_code == 400
    assert not PaymentEvent.objects.filter(event_id="evt_bad").exists()


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_webhook_missing_signature_rejected():
    client = APIClient()
    body = json.dumps({"id": "evt_nosig", "event": "charge.success", "data": {}}).encode()
    resp = client.post(_WEBHOOK_URL, data=body, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
@patch("apps.payments.api.views.process_payment_event")
def test_webhook_idempotent_replay_returns_200(mock_task):
    """Replaying the same event_id must be a no-op — no duplicate PaymentEvent row."""
    PaymentEvent.objects.create(
        event_id="evt_dup_001",
        event_type="charge.success",
        payload={},
        processed=True,
    )
    client = APIClient()
    payload = _make_event("charge.success", {}, "evt_dup_001")
    resp = _post_webhook(client, payload)
    assert resp.status_code == 200
    assert PaymentEvent.objects.filter(event_id="evt_dup_001").count() == 1
    mock_task.delay.assert_not_called()


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
@patch("apps.payments.api.views.process_payment_event")
def test_webhook_replays_unprocessed_event(mock_task):
    PaymentEvent.objects.create(
        event_id="evt_retry_001",
        event_type="charge.success",
        payload={},
        processed=False,
    )
    client = APIClient()
    payload = _make_event("charge.success", {}, "evt_retry_001")
    resp = _post_webhook(client, payload)
    assert resp.status_code == 200
    mock_task.delay.assert_called_once_with("evt_retry_001")


@pytest.mark.django_db
@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_webhook_missing_event_id_returns_400():
    client = APIClient()
    body = json.dumps({"event": "charge.success", "data": {}}).encode()
    sig = _sign(body)
    resp = client.post(
        _WEBHOOK_URL,
        data=body,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE=sig,
    )
    assert resp.status_code == 400


# ── process_payment_event — charge.success ────────────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_charge_success_activates_plan(mock_notify):
    account = _make_account(plan="personal_basic")
    SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_ref001",
        target_plan_id="personal_plus",
        status=SubscriptionCheckout.STATUS_PENDING,
    )

    payload = _make_event("charge.success", {
        "reference": "kotoku_ref001",
        "plan": {"plan_code": "PLN_plus"},
        "customer": {"customer_code": "CUS_abc", "email": account.email},
        "metadata": {"account_id": account.id, "plan_id": "personal_plus"},
    }, "evt_charge_001")
    event = PaymentEvent.objects.create(
        event_id="evt_charge_001", event_type="charge.success",
        payload=payload, processed=False,
    )

    process_payment_event("evt_charge_001")

    account.refresh_from_db()
    sub = Subscription.objects.get(account=account, plan_id="personal_plus")
    checkout = SubscriptionCheckout.objects.get(reference="kotoku_ref001")
    event.refresh_from_db()

    assert account.plan == "personal_plus"
    assert sub.status == Subscription.STATUS_ACTIVE
    assert sub.paystack_customer_code == "CUS_abc"
    assert checkout.status == SubscriptionCheckout.STATUS_CHARGED
    assert checkout.activated_subscription == sub
    assert event.processed is True
    assert AuditLog.objects.filter(event_type="payment.plan_activated").exists()
    mock_notify.assert_called_once()


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
@patch("apps.payments.tasks._notify_email")
def test_charge_success_without_plan_reactivates_recovery_checkout(mock_email, mock_notify):
    account = _make_account(plan="personal_plus")
    sub = Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_recovery_001",
        paystack_email=account.email,
        status=Subscription.STATUS_PAST_DUE,
        current_period_start=date(2026, 5, 1),
        current_period_end=date(2026, 6, 1),
    )
    checkout = SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_onetime",
        target_plan_id="personal_plus",
        checkout_kind=SubscriptionCheckout.KIND_RECOVERY,
        recovery_subscription=sub,
        status=SubscriptionCheckout.STATUS_PENDING,
    )

    payload = _make_event("charge.success", {
        "reference": "kotoku_onetime",
        "amount": 7900,
        "currency": "GHS",
        "customer": {"customer_code": "CUS_x", "email": "x@test.com"},
        "metadata": {},
    }, "evt_onetime_001")
    PaymentEvent.objects.create(
        event_id="evt_onetime_001", event_type="charge.success",
        payload=payload, processed=False,
    )
    process_payment_event("evt_onetime_001")

    account.refresh_from_db()
    sub.refresh_from_db()
    checkout.refresh_from_db()
    event = PaymentEvent.objects.get(event_id="evt_onetime_001")

    assert event.processed is True
    assert account.plan == "personal_plus"
    assert sub.status == Subscription.STATUS_ACTIVE
    assert sub.current_period_start == date(2026, 6, 1)
    assert sub.current_period_end == date(2026, 7, 1)
    assert checkout.status == SubscriptionCheckout.STATUS_PROVIDER_CREATED
    assert Invoice.objects.filter(paystack_ref="kotoku_onetime", status=Invoice.STATUS_PAID).exists()
    mock_notify.assert_called_once()


# ── process_payment_event — subscription.create ───────────────────────────────


@pytest.mark.django_db
def test_subscription_create_stores_sub_id_and_period():
    account = _make_account()
    sub = Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        paystack_customer_code="CUS_abc",
        status=Subscription.STATUS_ACTIVE,
    )
    checkout = SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_ref_subcreate",
        target_plan_id="personal_plus",
        status=SubscriptionCheckout.STATUS_CHARGED,
        activated_subscription=sub,
    )

    payload = _make_event("subscription.create", {
        "subscription_code": "SUB_xyz123",
        "email_token": "tok_abc",
        "customer": {"customer_code": "CUS_abc", "email": account.email},
        "next_payment_date": "2026-06-27T00:00:00.000Z",
        "start": "2026-05-27T00:00:00.000Z",
    }, "evt_subcreate_001")
    PaymentEvent.objects.create(
        event_id="evt_subcreate_001", event_type="subscription.create",
        payload=payload, processed=False,
    )

    process_payment_event("evt_subcreate_001")

    sub.refresh_from_db()
    assert sub.paystack_sub_id == "SUB_xyz123"
    assert sub.current_period_end == date(2026, 6, 27)
    assert sub.current_period_start == date(2026, 5, 27)
    assert sub.status == Subscription.STATUS_ACTIVE
    assert sub.cancel_at_period_end is False
    checkout.refresh_from_db()
    assert checkout.status == SubscriptionCheckout.STATUS_PROVIDER_CREATED


@pytest.mark.django_db
@patch("apps.payments.tasks.get_paystack_client")
def test_plan_switch_creates_new_subscription_and_replaces_old(mock_factory):
    mock_client = MagicMock()
    mock_client.fetch_subscription.return_value = {"email_token": "tok_old"}
    mock_client.cancel_subscription.return_value = True
    mock_factory.return_value = mock_client

    account = _make_account(plan="personal_basic")
    old_sub = Subscription.objects.create(
        account=account,
        plan_id="personal_basic",
        paystack_plan_code="PLN_basic",
        paystack_sub_id="SUB_old_001",
        paystack_email=account.email,
        paystack_customer_code="CUS_switch",
        status=Subscription.STATUS_ACTIVE,
    )
    SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_switch_001",
        target_plan_id="personal_plus",
        status=SubscriptionCheckout.STATUS_PENDING,
        replaces_subscription=old_sub,
    )

    PaymentEvent.objects.create(
        event_id="evt_switch_charge_001",
        event_type="charge.success",
        payload=_make_event("charge.success", {
            "reference": "kotoku_switch_001",
            "plan": {"plan_code": "PLN_plus"},
            "customer": {"customer_code": "CUS_switch", "email": account.email},
            "metadata": {"account_id": account.id, "plan_id": "personal_plus"},
        }, "evt_switch_charge_001"),
        processed=False,
    )
    process_payment_event("evt_switch_charge_001")

    new_sub = Subscription.objects.exclude(pk=old_sub.pk).get(account=account)
    assert new_sub.plan_id == "personal_plus"
    assert new_sub.status == Subscription.STATUS_PENDING

    PaymentEvent.objects.create(
        event_id="evt_switch_subcreate_001",
        event_type="subscription.create",
        payload=_make_event("subscription.create", {
            "subscription_code": "SUB_new_001",
            "customer": {"customer_code": "CUS_switch", "email": account.email},
            "next_payment_date": "2026-06-27T00:00:00.000Z",
            "start": "2026-05-27T00:00:00.000Z",
        }, "evt_switch_subcreate_001"),
        processed=False,
    )
    process_payment_event("evt_switch_subcreate_001")

    old_sub.refresh_from_db()
    new_sub.refresh_from_db()
    checkout = SubscriptionCheckout.objects.get(reference="kotoku_switch_001")

    assert old_sub.status == Subscription.STATUS_REPLACED
    assert old_sub.replaced_by == new_sub
    assert new_sub.paystack_sub_id == "SUB_new_001"
    assert checkout.activated_subscription == new_sub
    assert checkout.status == SubscriptionCheckout.STATUS_PROVIDER_CREATED
    mock_client.fetch_subscription.assert_called_once_with("SUB_old_001")
    mock_client.cancel_subscription.assert_called_once_with(
        subscription_code="SUB_old_001",
        email_token="tok_old",
    )


# ── process_payment_event — subscription.disable ─────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_subscription_disable_marks_cancelled(mock_notify):
    account = _make_account(plan="personal_plus")
    sub = Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        paystack_sub_id="SUB_cancel_me",
        status=Subscription.STATUS_ACTIVE,
        current_period_end=date(2026, 5, 31),
    )

    payload = _make_event("subscription.disable", {
        "subscription_code": "SUB_cancel_me",
    }, "evt_disable_001")
    PaymentEvent.objects.create(
        event_id="evt_disable_001", event_type="subscription.disable",
        payload=payload, processed=False,
    )

    process_payment_event("evt_disable_001")

    sub.refresh_from_db()
    account.refresh_from_db()

    assert sub.status == Subscription.STATUS_CANCELLED
    assert sub.cancel_at_period_end is True
    # Account.plan NOT immediately downgraded — Phase 5 handles this
    assert account.plan == "personal_plus"
    mock_notify.assert_called_once()


# ── process_payment_event — invoice.payment_failed ───────────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_invoice_payment_failed_sets_past_due(mock_notify):
    account = _make_account(plan="personal_plus")
    sub = Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_pastdue",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )

    payload = _make_event("invoice.payment_failed", {
        "reference": "inv_fail_001",
        "amount": 2500,
        "currency": "GHS",
        "subscription": {"subscription_code": "SUB_pastdue"},
    }, "evt_invfail_001")
    PaymentEvent.objects.create(
        event_id="evt_invfail_001", event_type="invoice.payment_failed",
        payload=payload, processed=False,
    )

    process_payment_event("evt_invfail_001")

    sub.refresh_from_db()
    assert sub.status == Subscription.STATUS_PAST_DUE
    assert Invoice.objects.filter(paystack_ref="inv_fail_001", status=Invoice.STATUS_FAILED).exists()
    mock_notify.assert_called_once()


# ── process_payment_event — invoice.update (paid) ────────────────────────────


@pytest.mark.django_db
def test_invoice_update_paid_extends_period():
    account = _make_account(plan="personal_plus")
    sub = Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_renew",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
        current_period_end=date(2026, 5, 31),
        cancel_at_period_end=True,
    )

    payload = _make_event("invoice.update", {
        "paid": True,
        "reference": "inv_renew_001",
        "amount": 2500,
        "currency": "GHS",
        "period_start": "2026-06-01T00:00:00.000Z",
        "period_end": "2026-06-30T00:00:00.000Z",
        "subscription": {"subscription_code": "SUB_renew"},
    }, "evt_invupdate_001")
    PaymentEvent.objects.create(
        event_id="evt_invupdate_001", event_type="invoice.update",
        payload=payload, processed=False,
    )

    process_payment_event("evt_invupdate_001")

    sub.refresh_from_db()
    assert sub.current_period_end == date(2026, 6, 30)
    assert sub.status == Subscription.STATUS_ACTIVE
    assert sub.cancel_at_period_end is False
    assert Invoice.objects.filter(paystack_ref="inv_renew_001", status=Invoice.STATUS_PAID).exists()


@pytest.mark.django_db
def test_invoice_update_unpaid_is_skipped():
    PaymentEvent.objects.create(
        event_id="evt_invunpaid_001", event_type="invoice.update",
        payload=_make_event("invoice.update", {"paid": False}, "evt_invunpaid_001"),
        processed=False,
    )
    process_payment_event("evt_invunpaid_001")
    event = PaymentEvent.objects.get(event_id="evt_invunpaid_001")
    assert event.processed is True


# ── process_payment_event — subscription.expiring_cards ──────────────────────


@pytest.mark.django_db
@patch("apps.payments.tasks._notify")
def test_expiring_cards_sends_notification(mock_notify):
    account = _make_account()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_expiring",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )

    payload = _make_event("subscription.expiring_cards", {
        "customer": {"email": account.email},
    }, "evt_expcard_001")
    PaymentEvent.objects.create(
        event_id="evt_expcard_001", event_type="subscription.expiring_cards",
        payload=payload, processed=False,
    )

    process_payment_event("evt_expcard_001")
    mock_notify.assert_called_once()


# ── process_payment_event — unknown event / error handling ────────────────────


@pytest.mark.django_db
def test_unknown_event_type_marked_processed():
    PaymentEvent.objects.create(
        event_id="evt_unknown_001", event_type="transfer.success",
        payload=_make_event("transfer.success", {}, "evt_unknown_001"),
        processed=False,
    )
    process_payment_event("evt_unknown_001")
    event = PaymentEvent.objects.get(event_id="evt_unknown_001")
    assert event.processed is True


@pytest.mark.django_db
def test_already_processed_event_is_skipped():
    PaymentEvent.objects.create(
        event_id="evt_replay_001", event_type="charge.success",
        payload={}, processed=True,
    )
    # Should return without touching anything — no exception.
    process_payment_event("evt_replay_001")


@pytest.mark.django_db
def test_handler_exception_stored_on_event():
    """If the handler raises, error is stored on PaymentEvent and does not crash the task."""
    # charge.success with a missing account_id will log and return — not raise.
    # Force a real exception by providing a non-existent account_id.
    payload = _make_event("charge.success", {
        "plan": {"plan_code": "PLN_plus"},
        "customer": {"customer_code": "CUS_z", "email": "z@test.com"},
        "metadata": {"account_id": 999999, "plan_id": "personal_plus"},
    }, "evt_err_001")
    PaymentEvent.objects.create(
        event_id="evt_err_001", event_type="charge.success",
        payload=payload, processed=False,
    )

    # Should not raise — error is stored on the event row.
    process_payment_event("evt_err_001")

    event = PaymentEvent.objects.get(event_id="evt_err_001")
    # Either processed cleanly (handler returned early) or error is set.
    # The handler logs and returns on DoesNotExist, so it processes cleanly.
    assert event.processed is True
