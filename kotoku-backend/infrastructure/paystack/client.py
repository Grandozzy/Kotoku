"""
Paystack HTTP adapter.

All Paystack API calls go through this module.
No view, service, or task should import requests/httpx and call Paystack directly.

Usage:
    from infrastructure.paystack.client import get_paystack_client
    client = get_paystack_client()
    result = client.initialize_transaction(...)

The secret key is read from Django settings (PAYSTACK_SECRET_KEY).
To switch from test to live: update the env var in Railway. No code change required.
"""

import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("kotoku")

_BASE_URL = "https://api.paystack.co"


# ── Data shapes returned to callers ──────────────────────────────────────────


@dataclass(frozen=True)
class InitializeResult:
    authorization_url: str
    access_code: str
    reference: str


@dataclass(frozen=True)
class SubscriptionResult:
    subscription_code: str
    customer_code: str
    plan_code: str
    status: str
    email_token: str


# ── Internal helpers ──────────────────────────────────────────────────────────


class PaystackError(Exception):
    """Raised when the Paystack API returns a non-success response."""

    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


def _request(method: str, path: str, secret_key: str, body: dict | None = None) -> dict:
    """
    Perform a single Paystack API request.
    Returns the parsed JSON body on success.
    Raises PaystackError on HTTP error or Paystack-level failure.
    """
    url = f"{_BASE_URL}{path}"
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        message = payload.get("message", raw or "Paystack HTTP error")
        logger.error("Paystack %s %s → HTTP %d: %s", method, path, exc.code, message)
        raise PaystackError(message, status_code=exc.code) from exc
    except Exception as exc:
        logger.exception("Paystack %s %s → network error", method, path)
        raise PaystackError(f"Network error calling Paystack: {exc}") from exc

    if not payload.get("status"):
        message = payload.get("message", "Paystack returned status=false")
        logger.error("Paystack %s %s → status=false: %s", method, path, message)
        raise PaystackError(message)

    return payload.get("data", {})


# ── Client ────────────────────────────────────────────────────────────────────


class PaystackClient:
    """
    Thin adapter over the Paystack REST API.

    Instantiate via get_paystack_client() so tests can patch the factory.
    Do not store state here — each method is a pure request→response mapping.
    """

    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise RuntimeError(
                "PAYSTACK_SECRET_KEY is not configured. "
                "Set it in your environment before using the payments feature."
            )
        self._key = secret_key

    # ── Transactions ──────────────────────────────────────────────────────────

    def initialize_transaction(
        self,
        *,
        email: str,
        amount_kobo: int,
        plan_code: str,
        reference: str,
        callback_url: str = "",
        metadata: dict | None = None,
    ) -> InitializeResult:
        """
        POST /transaction/initialize
        Returns the checkout URL, access code, and transaction reference.
        amount_kobo must be in the smallest currency unit (kobo for GHS: GHS × 100).
        """
        body: dict = {
            "email": email,
            "amount": amount_kobo,
            "plan": plan_code,
            "reference": reference,
        }
        if callback_url:
            body["callback_url"] = callback_url
        if metadata:
            body["metadata"] = metadata

        data = _request("POST", "/transaction/initialize", self._key, body)
        return InitializeResult(
            authorization_url=data["authorization_url"],
            access_code=data["access_code"],
            reference=data["reference"],
        )

    def verify_transaction(self, reference: str) -> dict:
        """
        GET /transaction/verify/{reference}
        Returns the full transaction data dict from Paystack.
        Raises PaystackError if the reference is unknown or the call fails.
        """
        return _request("GET", f"/transaction/verify/{urllib.parse.quote(reference, safe='')}", self._key)

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def create_subscription(
        self,
        *,
        customer_code: str,
        plan_code: str,
        authorization_code: str,
    ) -> SubscriptionResult:
        """
        POST /subscription
        Creates a Paystack subscription for an existing customer and authorization.
        Typically not called directly — Paystack auto-creates a subscription when
        initialize_transaction uses a plan code and the charge succeeds.
        Provided here for explicit subscription creation flows.
        """
        data = _request("POST", "/subscription", self._key, {
            "customer": customer_code,
            "plan": plan_code,
            "authorization": authorization_code,
        })
        return SubscriptionResult(
            subscription_code=data.get("subscription_code", ""),
            customer_code=data.get("customer", {}).get("customer_code", customer_code),
            plan_code=data.get("plan", {}).get("plan_code", plan_code),
            status=data.get("status", ""),
            email_token=data.get("email_token", ""),
        )

    def fetch_subscription(self, subscription_code: str) -> dict:
        """
        GET /subscription/{code}
        Returns the full subscription data dict.
        """
        return _request(
            "GET",
            f"/subscription/{urllib.parse.quote(subscription_code, safe='')}",
            self._key,
        )

    def cancel_subscription(
        self,
        *,
        subscription_code: str,
        email_token: str,
    ) -> bool:
        """
        POST /subscription/disable
        Cancels the subscription. Returns True on success.
        Raises PaystackError on failure.
        """
        _request("POST", "/subscription/disable", self._key, {
            "code": subscription_code,
            "token": email_token,
        })
        return True

    # ── Webhook signature ─────────────────────────────────────────────────────

    def verify_webhook_signature(self, payload_bytes: bytes, signature: str) -> bool:
        """
        Verify that an inbound webhook came from Paystack.

        Paystack signs the raw request body with HMAC-SHA512 using the webhook secret
        and sends the hex digest in the X-Paystack-Signature header.

        Uses hmac.compare_digest for constant-time comparison — never use == here.
        Returns True if the signature is valid, False otherwise.
        """
        webhook_secret = getattr(settings, "PAYSTACK_WEBHOOK_SECRET", "")
        if not webhook_secret:
            logger.error("PAYSTACK_WEBHOOK_SECRET is not set — rejecting webhook")
            return False

        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)


# ── Standalone webhook verification ──────────────────────────────────────────


def verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
    """
    Module-level webhook signature verification.
    Uses only PAYSTACK_WEBHOOK_SECRET — does not require PAYSTACK_SECRET_KEY.
    Use this in the webhook view instead of instantiating the full client.
    """
    webhook_secret = getattr(settings, "PAYSTACK_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("PAYSTACK_WEBHOOK_SECRET is not set — rejecting webhook")
        return False
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Factory ───────────────────────────────────────────────────────────────────


def get_paystack_client() -> PaystackClient:
    """
    Return a configured PaystackClient.
    Patch this function in tests to inject a mock client.

        with unittest.mock.patch("infrastructure.paystack.client.get_paystack_client") as m:
            m.return_value = mock_client
            ...
    """
    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    return PaystackClient(secret_key=secret_key)
