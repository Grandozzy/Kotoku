"""
Unit tests for infrastructure.paystack.client.

All Paystack HTTP calls are mocked — no live network requests are made.
Tests cover:
  - verify_webhook_signature with valid and tampered payloads
  - missing PAYSTACK_WEBHOOK_SECRET guard
  - missing PAYSTACK_SECRET_KEY guard
  - initialize_transaction happy path
  - cancel_subscription happy path
  - PaystackError raised on HTTP error responses
  - PaystackError raised on status=false responses
"""

import hashlib
import hmac
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from infrastructure.paystack.client import (
    InitializeResult,
    PaystackClient,
    PaystackError,
    get_paystack_client,
)

_TEST_SECRET = "sk_test_abc123"
_WEBHOOK_SECRET = "whsec_test_xyz"


def _make_client(secret: str = _TEST_SECRET) -> PaystackClient:
    return PaystackClient(secret_key=secret)


def _sign(payload_bytes: bytes, secret: str = _WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha512).hexdigest()


# ── verify_webhook_signature ──────────────────────────────────────────────────


@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_valid_signature_accepted():
    client = _make_client()
    payload = b'{"event":"charge.success"}'
    sig = _sign(payload)
    assert client.verify_webhook_signature(payload, sig) is True


@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_tampered_payload_rejected():
    client = _make_client()
    payload = b'{"event":"charge.success"}'
    sig = _sign(payload)
    tampered = b'{"event":"charge.success","extra":"hack"}'
    assert client.verify_webhook_signature(tampered, sig) is False


@override_settings(PAYSTACK_WEBHOOK_SECRET=_WEBHOOK_SECRET)
def test_wrong_signature_rejected():
    client = _make_client()
    payload = b'{"event":"charge.success"}'
    assert client.verify_webhook_signature(payload, "deadbeef" * 16) is False


@override_settings(PAYSTACK_WEBHOOK_SECRET="")
def test_missing_webhook_secret_rejects_all():
    client = _make_client()
    payload = b'{"event":"charge.success"}'
    sig = _sign(payload, secret="anything")
    assert client.verify_webhook_signature(payload, sig) is False


# ── PaystackClient construction ───────────────────────────────────────────────


def test_empty_secret_key_raises():
    with pytest.raises(RuntimeError, match="PAYSTACK_SECRET_KEY"):
        PaystackClient(secret_key="")


@override_settings(PAYSTACK_SECRET_KEY=_TEST_SECRET)
def test_get_paystack_client_factory():
    client = get_paystack_client()
    assert isinstance(client, PaystackClient)


@override_settings(PAYSTACK_SECRET_KEY="")
def test_get_paystack_client_raises_when_unconfigured():
    with pytest.raises(RuntimeError, match="PAYSTACK_SECRET_KEY"):
        get_paystack_client()


# ── initialize_transaction ────────────────────────────────────────────────────


def _mock_urlopen(response_body: dict):
    """Return a context manager mock that yields a file-like response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({"status": True, "data": response_body}).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


@patch("infrastructure.paystack.client.urllib.request.urlopen")
def test_initialize_transaction_happy_path(mock_urlopen):
    mock_urlopen.return_value = _mock_urlopen({
        "authorization_url": "https://checkout.paystack.com/abc",
        "access_code": "acc_123",
        "reference": "kotoku_ref001",
    })

    client = _make_client()
    result = client.initialize_transaction(
        email="user@example.com",
        amount_kobo=2500,
        plan_code="PLN_abc",
        reference="kotoku_ref001",
    )

    assert isinstance(result, InitializeResult)
    assert result.authorization_url == "https://checkout.paystack.com/abc"
    assert result.access_code == "acc_123"
    assert result.reference == "kotoku_ref001"


@patch("infrastructure.paystack.client.urllib.request.urlopen")
def test_initialize_transaction_sends_correct_body(mock_urlopen):
    mock_urlopen.return_value = _mock_urlopen({
        "authorization_url": "https://checkout.paystack.com/abc",
        "access_code": "acc_123",
        "reference": "kotoku_ref001",
    })

    client = _make_client()
    client.initialize_transaction(
        email="user@example.com",
        amount_kobo=2500,
        plan_code="PLN_abc",
        reference="kotoku_ref001",
        callback_url="kotoku://payment/callback",
        metadata={"account_id": 42, "plan_id": "personal_plus"},
    )

    call_args = mock_urlopen.call_args
    req = call_args[0][0]
    body = json.loads(req.data.decode())
    assert body["email"] == "user@example.com"
    assert body["amount"] == 2500
    assert body["plan"] == "PLN_abc"
    assert body["callback_url"] == "kotoku://payment/callback"
    assert body["metadata"]["account_id"] == 42


# ── cancel_subscription ───────────────────────────────────────────────────────


@patch("infrastructure.paystack.client.urllib.request.urlopen")
def test_cancel_subscription_returns_true(mock_urlopen):
    mock_urlopen.return_value = _mock_urlopen({})

    client = _make_client()
    result = client.cancel_subscription(
        subscription_code="SUB_abc123",
        email_token="token_xyz",
    )
    assert result is True


# ── error handling ────────────────────────────────────────────────────────────


@patch("infrastructure.paystack.client.urllib.request.urlopen")
def test_http_error_raises_paystack_error(mock_urlopen):
    import urllib.error

    error_body = json.dumps({"status": False, "message": "Invalid key"}).encode()
    http_error = urllib.error.HTTPError(
        url="https://api.paystack.co/transaction/initialize",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=BytesIO(error_body),
    )
    mock_urlopen.side_effect = http_error

    client = _make_client()
    with pytest.raises(PaystackError, match="Invalid key") as exc_info:
        client.initialize_transaction(
            email="user@example.com",
            amount_kobo=1000,
            plan_code="PLN_abc",
            reference="ref_001",
        )
    assert exc_info.value.status_code == 401


@patch("infrastructure.paystack.client.urllib.request.urlopen")
def test_status_false_raises_paystack_error(mock_urlopen):
    resp = MagicMock()
    resp.read.return_value = json.dumps({
        "status": False,
        "message": "Duplicate transaction reference",
    }).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = resp

    client = _make_client()
    with pytest.raises(PaystackError, match="Duplicate transaction reference"):
        client.initialize_transaction(
            email="user@example.com",
            amount_kobo=1000,
            plan_code="PLN_abc",
            reference="ref_dup",
        )


@patch("infrastructure.paystack.client.urllib.request.urlopen")
def test_network_error_raises_paystack_error(mock_urlopen):
    mock_urlopen.side_effect = OSError("Connection refused")

    client = _make_client()
    with pytest.raises(PaystackError, match="Network error"):
        client.initialize_transaction(
            email="user@example.com",
            amount_kobo=1000,
            plan_code="PLN_abc",
            reference="ref_net",
        )
