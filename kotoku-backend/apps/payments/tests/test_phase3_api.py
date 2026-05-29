"""
Phase 3 tests — subscription initiation API.

All Paystack HTTP calls are mocked via patch on get_paystack_client.
Tests cover:
  - GET /api/payments/config/
  - POST /api/payments/initiate/ — happy path, invalid plan, missing plan code,
    duplicate active subscription, Paystack error
  - GET /api/payments/subscription/ — no subscription, active subscription
  - POST /api/payments/cancel/ — happy path, no subscription, pending subscription,
    missing paystack_sub_id, Paystack error
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, User
from apps.payments.models import Subscription, SubscriptionCheckout
from infrastructure.paystack.client import InitializeResult, PaystackError

_CONFIG_URL = "/api/payments/config/"
_INITIATE_URL = "/api/payments/initiate/"
_SUBSCRIPTION_URL = "/api/payments/subscription/"
_CANCEL_URL = "/api/payments/cancel/"

_PLAN_CODES = {
    "personal_basic": "PLN_basic",
    "personal_plus": "PLN_plus",
    "personal_protect": "PLN_protect",
    "enterprise_standard": "PLN_ent_std",
    "enterprise_plus": "PLN_ent_plus",
}

_seq = 0


def _make_account_client(plan: str = "personal_basic") -> tuple[Account, APIClient]:
    global _seq
    _seq += 1
    phone = f"+233200{_seq:06d}"
    user = User.objects.create_user(phone=phone)
    account = Account.objects.create(
        user=user,
        email=f"pay{_seq}@test.com",
        phone=phone,
        plan=plan,
    )
    token = AccessToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return account, client


def _mock_client(
    authorization_url="https://checkout.paystack.com/abc",
    access_code="acc_test",
    reference="kotoku_ref001",
) -> MagicMock:
    mock = MagicMock()
    mock.initialize_transaction.return_value = InitializeResult(
        authorization_url=authorization_url,
        access_code=access_code,
        reference=reference,
    )
    mock.fetch_subscription.return_value = {"email_token": "tok_email_xyz"}
    mock.cancel_subscription.return_value = True
    return mock


# ── Config endpoint ───────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(PAYSTACK_PUBLIC_KEY="pk_test_abc123")
def test_config_returns_public_key():
    _, client = _make_account_client()
    resp = client.get(_CONFIG_URL)
    assert resp.status_code == 200
    assert resp.json()["data"]["paystack_public_key"] == "pk_test_abc123"


@pytest.mark.django_db
def test_config_requires_auth():
    resp = APIClient().get(_CONFIG_URL)
    assert resp.status_code == 401


# ── POST /api/payments/initiate/ ──────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES=_PLAN_CODES, PAYSTACK_CALLBACK_URL="kotoku://cb")
@patch("apps.payments.services.get_paystack_client")
def test_initiate_happy_path(mock_factory):
    mock_factory.return_value = _mock_client(reference="kotoku_xyz")
    account, client = _make_account_client()

    resp = client.post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["authorization_url"] == "https://checkout.paystack.com/abc"
    assert data["access_code"] == "acc_test"
    assert data["reference"] == "kotoku_xyz"

    checkout = SubscriptionCheckout.objects.get(account=account, reference="kotoku_xyz")
    assert checkout.status == SubscriptionCheckout.STATUS_PENDING
    assert checkout.target_plan_id == "personal_plus"
    assert checkout.authorization_url == "https://checkout.paystack.com/abc"
    assert checkout.access_code == "acc_test"
    assert not Subscription.objects.filter(account=account).exists()


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES=_PLAN_CODES)
@patch("apps.payments.services.get_paystack_client")
def test_initiate_passes_correct_args_to_paystack(mock_factory):
    mock = _mock_client()
    mock_factory.return_value = mock
    account, client = _make_account_client()

    client.post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")

    mock.initialize_transaction.assert_called_once()
    call_kwargs = mock.initialize_transaction.call_args.kwargs
    assert call_kwargs["email"] == account.email
    assert call_kwargs["amount_kobo"] == 2500  # GHS 25 × 100
    assert call_kwargs["plan_code"] == "PLN_plus"
    assert call_kwargs["metadata"]["plan_id"] == "personal_plus"
    assert call_kwargs["metadata"]["account_id"] == account.id


@pytest.mark.django_db
def test_initiate_invalid_plan_id():
    _, client = _make_account_client()
    resp = client.post(_INITIATE_URL, {"plan_id": "made_up_plan"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES={k: "" for k in _PLAN_CODES})
def test_initiate_unconfigured_plan_code_returns_400():
    _, client = _make_account_client()
    resp = client.post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")
    assert resp.status_code == 400
    assert "not yet available" in resp.json()["message"]


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES=_PLAN_CODES)
@patch("apps.payments.services.get_paystack_client")
def test_initiate_rejects_duplicate_active_same_plan(mock_factory):
    mock_factory.return_value = _mock_client()
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )

    resp = client.post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")

    assert resp.status_code == 400
    assert "already have an active subscription" in resp.json()["message"]


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES=_PLAN_CODES)
@patch("apps.payments.services.get_paystack_client")
def test_initiate_allows_upgrade_from_active_different_plan(mock_factory):
    mock_factory.return_value = _mock_client(reference="kotoku_upgrade")
    account, client = _make_account_client()
    active_sub = Subscription.objects.create(
        account=account,
        plan_id="personal_basic",
        paystack_plan_code="PLN_basic",
        paystack_sub_id="SUB_old_active",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )

    # Upgrading to a different plan should be allowed
    resp = client.post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")

    assert resp.status_code == 201
    checkout = SubscriptionCheckout.objects.get(reference="kotoku_upgrade")
    assert checkout.replaces_subscription == active_sub
    assert checkout.target_plan_id == "personal_plus"


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES=_PLAN_CODES)
@patch("apps.payments.services.get_paystack_client")
def test_initiate_rejects_when_checkout_already_open(mock_factory):
    mock_factory.return_value = _mock_client()
    account, client = _make_account_client()
    SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_existing",
        target_plan_id="personal_plus",
        status=SubscriptionCheckout.STATUS_PENDING,
    )

    resp = client.post(_INITIATE_URL, {"plan_id": "enterprise_standard"}, format="json")

    assert resp.status_code == 400
    assert "already in progress" in resp.json()["message"]


@pytest.mark.django_db
@override_settings(PAYSTACK_PLAN_CODES=_PLAN_CODES)
@patch("apps.payments.services.get_paystack_client")
def test_initiate_paystack_error_returns_400(mock_factory):
    mock = _mock_client()
    mock.initialize_transaction.side_effect = PaystackError("Gateway down", status_code=503)
    mock_factory.return_value = mock
    _, client = _make_account_client()

    resp = client.post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")

    assert resp.status_code == 400
    assert "Payment gateway error" in resp.json()["message"]


@pytest.mark.django_db
def test_initiate_requires_auth():
    resp = APIClient().post(_INITIATE_URL, {"plan_id": "personal_plus"}, format="json")
    assert resp.status_code == 401


# ── GET /api/payments/subscription/ ──────────────────────────────────────────


@pytest.mark.django_db
def test_subscription_status_no_subscription():
    _, client = _make_account_client()
    resp = client.get(_SUBSCRIPTION_URL)
    assert resp.status_code == 200
    assert resp.json()["data"] == {"has_subscription": False}


@pytest.mark.django_db
def test_subscription_status_active():
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_sub_id="SUB_abc",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
        current_period_start=date(2026, 5, 1),
        current_period_end=date(2026, 5, 31),
        cancel_at_period_end=False,
    )

    resp = client.get(_SUBSCRIPTION_URL)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["has_subscription"] is True
    assert data["plan_id"] == "personal_plus"
    assert data["status"] == "active"
    assert data["current_period_end"] == "2026-05-31"
    assert data["cancel_at_period_end"] is False


@pytest.mark.django_db
def test_subscription_status_pending():
    account, client = _make_account_client()
    SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_pending_001",
        target_plan_id="personal_basic",
        status=SubscriptionCheckout.STATUS_PENDING,
    )

    resp = client.get(_SUBSCRIPTION_URL)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert data["current_period_end"] is None


@pytest.mark.django_db
def test_subscription_status_requires_auth():
    resp = APIClient().get(_SUBSCRIPTION_URL)
    assert resp.status_code == 401


# ── POST /api/payments/cancel/ ────────────────────────────────────────────────


@pytest.mark.django_db
@patch("apps.payments.services.get_paystack_client")
def test_cancel_happy_path(mock_factory):
    mock_factory.return_value = _mock_client()
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_sub_id="SUB_abc123",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
        current_period_end=date(2026, 5, 31),
    )

    resp = client.post(_CANCEL_URL)

    assert resp.status_code == 200
    assert "cancelled at the end" in resp.json()["data"]["detail"]

    sub = Subscription.objects.get(account=account, paystack_sub_id="SUB_abc123")
    assert sub.cancel_at_period_end is True
    assert sub.status == Subscription.STATUS_ACTIVE  # not downgraded yet


@pytest.mark.django_db
@patch("apps.payments.services.get_paystack_client")
def test_cancel_calls_paystack_with_correct_args(mock_factory):
    mock = _mock_client()
    mock_factory.return_value = mock
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_sub_id="SUB_xyz",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )

    client.post(_CANCEL_URL)

    mock.fetch_subscription.assert_called_once_with("SUB_xyz")
    mock.cancel_subscription.assert_called_once_with(
        subscription_code="SUB_xyz",
        email_token="tok_email_xyz",
    )


@pytest.mark.django_db
@patch("apps.payments.services.get_paystack_client")
def test_cancel_targets_current_subscription_when_switch_checkout_pending(mock_factory):
    mock = _mock_client()
    mock_factory.return_value = mock
    account, client = _make_account_client(plan="personal_basic")
    current_sub = Subscription.objects.create(
        account=account,
        plan_id="personal_basic",
        paystack_plan_code="PLN_basic",
        paystack_sub_id="SUB_current_live",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )
    SubscriptionCheckout.objects.create(
        account=account,
        reference="kotoku_switch_pending",
        target_plan_id="personal_plus",
        status=SubscriptionCheckout.STATUS_PENDING,
        replaces_subscription=current_sub,
    )

    resp = client.post(_CANCEL_URL)

    assert resp.status_code == 200
    mock.fetch_subscription.assert_called_once_with("SUB_current_live")
    mock.cancel_subscription.assert_called_once_with(
        subscription_code="SUB_current_live",
        email_token="tok_email_xyz",
    )


@pytest.mark.django_db
def test_cancel_no_subscription_returns_400():
    _, client = _make_account_client()
    resp = client.post(_CANCEL_URL)
    assert resp.status_code == 400
    assert "No subscription found" in resp.json()["message"]


@pytest.mark.django_db
def test_cancel_pending_subscription_returns_400():
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        status=Subscription.STATUS_PENDING,
    )
    resp = client.post(_CANCEL_URL)
    assert resp.status_code == 400
    assert "No active subscription" in resp.json()["message"]


@pytest.mark.django_db
def test_cancel_active_without_sub_id_returns_400():
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
        paystack_sub_id="",  # not yet confirmed by webhook
    )
    resp = client.post(_CANCEL_URL)
    assert resp.status_code == 400
    assert "not yet confirmed" in resp.json()["message"]


@pytest.mark.django_db
@patch("apps.payments.services.get_paystack_client")
def test_cancel_paystack_error_returns_400(mock_factory):
    mock = _mock_client()
    mock.cancel_subscription.side_effect = PaystackError("Paystack error", status_code=500)
    mock_factory.return_value = mock
    account, client = _make_account_client()
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_plan_code="PLN_plus",
        paystack_sub_id="SUB_fail",
        paystack_email=account.email,
        status=Subscription.STATUS_ACTIVE,
    )

    resp = client.post(_CANCEL_URL)

    assert resp.status_code == 400
    assert "Payment gateway error" in resp.json()["message"]


@pytest.mark.django_db
def test_cancel_requires_auth():
    resp = APIClient().post(_CANCEL_URL)
    assert resp.status_code == 401
