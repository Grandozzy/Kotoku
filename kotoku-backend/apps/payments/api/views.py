import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.payments.api.serializers import InitiateSerializer
from apps.payments.models import PaymentEvent, SubscriptionCheckout
from apps.payments.selectors import get_subscription_status
from apps.payments.services import PaymentService
from apps.payments.tasks import process_payment_event
from common.exceptions import DomainError
from common.responses import ok
from infrastructure.paystack.client import verify_webhook_signature

logger = logging.getLogger("kotoku")


def _get_account(request):
    try:
        return request.user.account
    except Exception as exc:
        raise DomainError("Account not found for this user.") from exc


class ConfigView(APIView):
    """
    GET /api/payments/config/
    Returns the Paystack public key so the mobile client can initialise the
    Paystack SDK without the key being baked into the app bundle.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return ok({"paystack_public_key": settings.PAYSTACK_PUBLIC_KEY})


class InitiateView(APIView):
    """
    POST /api/payments/initiate/
    Body: { "plan_id": "personal_plus" }
    Starts a Paystack checkout and returns the authorization URL.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = _get_account(request)
        mode = serializer.validated_data.get("mode", InitiateSerializer.MODE_SUBSCRIPTION)
        if mode == InitiateSerializer.MODE_RECOVERY:
            result = PaymentService.initiate_recovery_payment(
                account=account,
                plan_id=serializer.validated_data["plan_id"],
                callback_url=serializer.validated_data.get("callback_url") or None,
                channels=serializer.validated_data.get("channels"),
            )
        else:
            result = PaymentService.initiate_subscription(
                account=account,
                plan_id=serializer.validated_data["plan_id"],
                callback_url=serializer.validated_data.get("callback_url") or None,
            )
        return ok({
            "authorization_url": result.authorization_url,
            "access_code": result.access_code,
            "reference": result.reference,
        }, status_code=201)


class SubscriptionView(APIView):
    """
    GET /api/payments/subscription/
    Returns the current subscription state for the authenticated account.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = _get_account(request)
        return ok(get_subscription_status(account))


class CancelCheckoutView(APIView):
    """
    POST /api/payments/checkout/cancel/
    Cancels any open (pending/charged) checkout for the account.
    Safe to call after abandoning the Paystack popup — if the user actually
    paid, Paystack's webhook will have already moved the checkout to a
    terminal status before this call arrives.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        account = _get_account(request)
        updated = SubscriptionCheckout.objects.filter(
            account=account,
            status__in=SubscriptionCheckout.OPEN_STATUSES,
        ).update(status=SubscriptionCheckout.STATUS_CANCELLED)
        logger.info("checkout/cancel account=%s cancelled=%d", account.id, updated)
        return ok({"cancelled": updated > 0})


class CancelView(APIView):
    """
    POST /api/payments/cancel/
    Marks the active subscription to cancel at period end. Does not refund.
    Account.plan is not changed immediately — the period-end task handles it.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        account = _get_account(request)
        PaymentService.cancel_subscription(account=account)
        msg = "Subscription will be cancelled at the end of the current billing period."
        return ok({"detail": msg})


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    """
    POST /api/payments/webhook/
    Unauthenticated — Paystack authenticates via HMAC-SHA512 signature.

    Flow:
      1. Read raw body bytes (before DRF parses anything).
      2. Verify X-Paystack-Signature header using PAYSTACK_WEBHOOK_SECRET.
      3. Idempotency check on event["id"].
      4. Persist PaymentEvent row.
      5. Dispatch process_payment_event Celery task.
      6. Return 200 immediately — never block on processing.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # Step 1: raw body for signature verification — must come before any parsing.
        body_bytes = request.body
        signature = request.headers.get("X-Paystack-Signature", "")

        # Step 2: verify signature — reject anything that doesn't match.
        if not verify_webhook_signature(body_bytes, signature):
            logger.warning(
                "Webhook signature verification failed — sig=%s ip=%s",
                signature[:16] if signature else "missing",
                request.META.get("REMOTE_ADDR"),
            )
            return HttpResponse(status=400)

        # Step 3: parse body.
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.error("Webhook body is not valid JSON")
            return HttpResponse(status=400)

        event_id = str(payload.get("id", ""))
        event_type = payload.get("event", "")

        if not event_id:
            logger.error("Webhook payload missing event id: %s", payload)
            return HttpResponse(status=400)

        # Step 4: idempotency check.
        existing = PaymentEvent.objects.filter(event_id=event_id).first()
        if existing:
            if existing.processed:
                logger.info("Webhook event_id=%s already processed — skipping", event_id)
                return HttpResponse(status=200)
            try:
                process_payment_event.delay(event_id)
            except Exception:
                logger.exception(
                    "Webhook event_id=%s exists but could not be re-dispatched",
                    event_id,
                )
                return HttpResponse(status=503)
            logger.info(
                "Webhook event_id=%s already recorded but unprocessed — re-dispatched", event_id
            )
            return HttpResponse(status=200)

        # Step 5: persist the event row.
        PaymentEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            processed=False,
        )

        # Step 6: dispatch to Celery and return immediately.
        try:
            process_payment_event.delay(event_id)
        except Exception:
            logger.exception("Webhook event_id=%s type=%s dispatch failed", event_id, event_type)
            return HttpResponse(status=503)
        logger.info("Webhook event_id=%s type=%s accepted", event_id, event_type)
        return HttpResponse(status=200)
