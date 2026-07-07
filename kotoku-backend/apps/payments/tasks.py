"""
Payment Celery tasks.

process_payment_event — dispatched by the webhook view for every verified Paystack event.
  - Re-fetches the PaymentEvent from DB (never trusts data passed through Celery args).
  - Each event type is handled by a dedicated _handle_* function.
  - Failures are recorded on PaymentEvent.error; they do not crash the task.

expire_lapsed_subscriptions — daily beat task (registered in settings).
  - Implemented in Phase 5.
"""

import logging
from datetime import date, datetime
from datetime import timezone as dt_timezone

from celery import shared_task
from django.db import transaction

from apps.audit.services import AuditService
from apps.notifications.models import Notification
from apps.payments.models import Invoice, PaymentEvent, Subscription, SubscriptionCheckout
from infrastructure.paystack.client import PaystackError, get_paystack_client

logger = logging.getLogger("kotoku")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _find_subscription_by_customer_code(customer_code: str) -> Subscription | None:
    return (
        Subscription.objects.filter(paystack_customer_code=customer_code)
        .exclude(status=Subscription.STATUS_REPLACED)
        .order_by("-created_at", "-id")
        .first()
    )


def _find_subscription_by_sub_id(sub_id: str) -> Subscription | None:
    return (
        Subscription.objects.filter(paystack_sub_id=sub_id)
        .exclude(status=Subscription.STATUS_REPLACED)
        .order_by("-created_at", "-id")
        .first()
    )


def _find_subscription_by_email(email: str) -> Subscription | None:
    return (
        Subscription.objects.filter(paystack_email=email)
        .exclude(status=Subscription.STATUS_REPLACED)
        .order_by("-created_at", "-id")
        .first()
    )


def _find_checkout_by_reference(reference: str) -> SubscriptionCheckout | None:
    return SubscriptionCheckout.objects.filter(reference=reference).first()


def _find_checkout_for_activated_subscription(sub: Subscription) -> SubscriptionCheckout | None:
    return (
        SubscriptionCheckout.objects.filter(activated_subscription=sub)
        .order_by("-created_at", "-id")
        .first()
    )


def _find_open_checkout_by_email(email: str) -> SubscriptionCheckout | None:
    return (
        SubscriptionCheckout.objects.filter(
            account__email=email,
            status__in=SubscriptionCheckout.OPEN_STATUSES + [SubscriptionCheckout.STATUS_PROVIDER_CREATED],
        )
        .order_by("-created_at", "-id")
        .first()
    )


def _cancel_replaced_subscription(old_sub: Subscription, new_sub: Subscription) -> None:
    if old_sub.status == Subscription.STATUS_REPLACED:
        return

    if old_sub.paystack_sub_id:
        try:
            client = get_paystack_client()
            paystack_data = client.fetch_subscription(old_sub.paystack_sub_id)
            email_token = paystack_data.get("email_token", "")
            if email_token:
                client.cancel_subscription(
                    subscription_code=old_sub.paystack_sub_id,
                    email_token=email_token,
                )
        except PaystackError:
            logger.exception(
                "Failed to cancel replaced Paystack subscription sub=%s replacement=%s",
                old_sub.pk,
                new_sub.pk,
            )

    old_sub.status = Subscription.STATUS_REPLACED
    old_sub.cancel_at_period_end = False
    old_sub.replaced_by = new_sub
    old_sub.save(update_fields=["status", "cancel_at_period_end", "replaced_by", "updated_at"])


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO-8601 datetime string from Paystack into a date."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(dt_timezone.utc).date()
    except (ValueError, AttributeError):
        return None


def _notify(account, body: str) -> None:
    """Send an SMS notification through the existing notifications app."""
    try:
        from apps.notifications.services import NotificationService
        NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.SMS,
            body=body,
        )
    except Exception:
        logger.exception("Failed to send payment SMS notification to account=%s", account.pk)


def _notify_email(account, *, subject: str, body: str) -> None:
    """Send an email notification through the existing notifications app."""
    if not account.email:
        logger.warning("No email address for account=%s — skipping email notification", account.pk)
        return
    try:
        from apps.notifications.services import NotificationService
        NotificationService.send_notification(
            account_id=account.pk,
            channel=Notification.Channel.EMAIL,
            subject=subject,
            body=body,
        )
    except Exception:
        logger.exception("Failed to send payment email notification to account=%s", account.pk)


# ── Event handlers ────────────────────────────────────────────────────────────


def _handle_charge_success(data: dict) -> None:
    """
    A charge completed successfully.
    If it is a subscription charge (data.plan present), activate the account's plan.
    We match the account via metadata.account_id which we set on initiate.
    """
    plan_info = data.get("plan") or {}
    if not plan_info:
        logger.info("charge.success has no plan — one-time charge, skipping")
        return

    reference = data.get("reference", "")
    metadata = data.get("metadata") or {}
    account_id = metadata.get("account_id")
    plan_id = metadata.get("plan_id")
    checkout = _find_checkout_by_reference(reference) if reference else None

    if checkout:
        account_id = checkout.account_id
        plan_id = checkout.target_plan_id

    if not account_id or not plan_id:
        logger.error("charge.success missing account_id/plan_id in metadata: %s", metadata)
        return

    customer = data.get("customer") or {}
    customer_code = customer.get("customer_code", "")
    customer_email = customer.get("email", "")

    from apps.accounts.models import Account
    try:
        account = Account.objects.get(pk=account_id)
    except Account.DoesNotExist:
        logger.error("charge.success: account_id=%s not found", account_id)
        return

    with transaction.atomic():
        sub = None
        locked_checkout = None
        next_status = Subscription.STATUS_ACTIVE
        if checkout:
            locked_checkout = SubscriptionCheckout.objects.select_for_update().get(pk=checkout.pk)
            if locked_checkout.replaces_subscription_id:
                next_status = Subscription.STATUS_PENDING
            if locked_checkout.activated_subscription_id:
                sub = Subscription.objects.select_for_update().get(pk=locked_checkout.activated_subscription_id)

        if sub is None:
            sub = Subscription.objects.create(
                account=account,
                plan_id=plan_id,
                paystack_plan_code=plan_info.get("plan_code", ""),
                paystack_email=customer_email or account.email,
                paystack_customer_code=customer_code,
                status=next_status,
                cancel_at_period_end=False,
            )
        else:
            sub.plan_id = plan_id
            if plan_info.get("plan_code"):
                sub.paystack_plan_code = plan_info.get("plan_code", "")
            sub.status = next_status
            sub.paystack_customer_code = customer_code
            sub.cancel_at_period_end = False
            if customer_email:
                sub.paystack_email = customer_email
            sub.save(update_fields=[
                "plan_id", "paystack_plan_code", "status", "paystack_customer_code",
                "paystack_email", "cancel_at_period_end", "updated_at",
            ])

        if locked_checkout:
            locked_checkout.status = SubscriptionCheckout.STATUS_CHARGED
            locked_checkout.activated_subscription = sub
            locked_checkout.save(update_fields=["status", "activated_subscription", "updated_at"])

        # Promote Account.plan — only verified webhook does this.
        if account.plan != plan_id:
            account.plan = plan_id
            account.save(update_fields=["plan", "updated_at"])

    AuditService.record_event(
        event_type="payment.plan_activated",
        entity_type="account",
        entity_id=str(account_id),
        actor=f"paystack:{customer_code}",
        metadata={"plan_id": plan_id, "customer_code": customer_code},
    )
    plan_name = plan_id.replace("_", " ").title()
    _notify(account, f"Your Kotoku {plan_name} subscription is now active.")
    _notify_email(
        account,
        subject=f"Your Kotoku {plan_name} subscription is active",
        body=(
            f"Hi {account.full_name or 'there'},\n\n"
            f"Your Kotoku {plan_name} subscription is now active.\n\n"
            "You can seal agreements up to your plan limit each month.\n\n"
            "The Kotoku team"
        ),
    )


def _handle_subscription_create(data: dict) -> None:
    """
    Paystack has created a subscription record. Store the sub ID and period dates.
    This fires after charge.success so the Subscription row already has status=active.
    """
    sub_code = data.get("subscription_code", "")
    customer = data.get("customer") or {}
    customer_code = customer.get("customer_code", "")
    next_payment = data.get("next_payment_date")
    start = data.get("start") or data.get("createdAt")
    customer_email = customer.get("email", "")

    sub = (
        Subscription.objects.filter(
            paystack_customer_code=customer_code,
            paystack_sub_id="",
        )
        .exclude(status=Subscription.STATUS_REPLACED)
        .order_by("-created_at", "-id")
        .first()
        or Subscription.objects.filter(
            paystack_email=customer_email,
            paystack_sub_id="",
        )
        .exclude(status=Subscription.STATUS_REPLACED)
        .order_by("-created_at", "-id")
        .first()
        or _find_subscription_by_customer_code(customer_code)
        or _find_subscription_by_email(customer_email)
    )

    if not sub:
        logger.error("subscription.create: no Subscription for customer_code=%s", customer_code)
        return

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(pk=sub.pk)
        sub.paystack_sub_id = sub_code
        sub.status = Subscription.STATUS_ACTIVE
        sub.current_period_start = _parse_date(start)
        sub.current_period_end = _parse_date(next_payment)
        sub.cancel_at_period_end = False
        sub.save(update_fields=[
            "paystack_sub_id", "status",
            "current_period_start", "current_period_end", "cancel_at_period_end", "updated_at",
        ])

        checkout = _find_checkout_for_activated_subscription(sub)
        if not checkout and customer_email:
            checkout = _find_open_checkout_by_email(customer_email)
        if checkout:
            checkout = SubscriptionCheckout.objects.select_for_update().get(pk=checkout.pk)
            checkout.activated_subscription = sub
            checkout.status = SubscriptionCheckout.STATUS_PROVIDER_CREATED
            checkout.save(update_fields=["activated_subscription", "status", "updated_at"])
            if checkout.replaces_subscription_id:
                old_sub = Subscription.objects.select_for_update().get(pk=checkout.replaces_subscription_id)
                _cancel_replaced_subscription(old_sub, sub)

    AuditService.record_event(
        event_type="payment.subscription_created",
        entity_type="subscription",
        entity_id=str(sub.pk),
        actor=f"paystack:{customer_code}",
        metadata={"sub_code": sub_code, "next_payment": next_payment},
    )


def _handle_subscription_disable(data: dict) -> None:
    """
    Paystack has disabled (cancelled) a subscription.
    Mark cancelled — the Phase 5 daily task handles the plan downgrade at period end.
    """
    sub_code = data.get("subscription_code", "")
    sub = _find_subscription_by_sub_id(sub_code)
    if not sub:
        logger.error("subscription.disable: no Subscription for sub_code=%s", sub_code)
        return

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(pk=sub.pk)
        sub.status = Subscription.STATUS_CANCELLED
        sub.cancel_at_period_end = True
        sub.save(update_fields=["status", "cancel_at_period_end", "updated_at"])

    AuditService.record_event(
        event_type="payment.subscription_cancelled",
        entity_type="subscription",
        entity_id=str(sub.pk),
        metadata={"sub_code": sub_code, "period_end": str(sub.current_period_end)},
    )
    _notify(
        sub.account,
        "Your Kotoku subscription has been cancelled. "
        "You will keep access until the end of your current billing period.",
    )


def _handle_invoice_payment_failed(data: dict) -> None:
    """
    A renewal charge failed. Move subscription to past_due.
    The Phase 5 task will downgrade once current_period_end passes.
    """
    subscription_data = data.get("subscription") or {}
    sub_code = subscription_data.get("subscription_code", "")
    sub = _find_subscription_by_sub_id(sub_code)

    if not sub:
        customer = data.get("customer") or {}
        sub = _find_subscription_by_email(customer.get("email", ""))

    if not sub:
        logger.error("invoice.payment_failed: no Subscription found for data=%s", data)
        return

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(pk=sub.pk)
        sub.status = Subscription.STATUS_PAST_DUE
        sub.cancel_at_period_end = False
        sub.save(update_fields=["status", "updated_at"])

    # Record failed invoice
    ref = data.get("reference", "")
    amount = data.get("amount", 0)
    if ref:
        Invoice.objects.get_or_create(
            paystack_ref=ref,
            defaults={
                "account": sub.account,
                "subscription": sub,
                "amount_kobo": amount,
                "currency": data.get("currency", "GHS"),
                "status": Invoice.STATUS_FAILED,
            },
        )

    AuditService.record_event(
        event_type="payment.invoice_failed",
        entity_type="subscription",
        entity_id=str(sub.pk),
        metadata={"sub_code": sub_code, "ref": ref},
    )
    _notify(
        sub.account,
        "Your Kotoku payment failed. Please update your card details to keep your subscription active.",
    )
    _notify_email(
        sub.account,
        subject="Action required: your Kotoku payment failed",
        body=(
            f"Hi {sub.account.full_name or 'there'},\n\n"
            "Your recent Kotoku payment failed and your subscription is now past due.\n\n"
            "Please update your card details to keep your subscription active "
            "and avoid losing access to your plan.\n\n"
            "The Kotoku team"
        ),
    )


def _handle_invoice_update(data: dict) -> None:
    """
    An invoice was updated. If paid=True, extend the billing period.
    """
    if not data.get("paid"):
        return

    subscription_data = data.get("subscription") or {}
    sub_code = subscription_data.get("subscription_code", "")
    sub = _find_subscription_by_sub_id(sub_code)
    if not sub:
        logger.info("invoice.update: no Subscription for sub_code=%s — skipping", sub_code)
        return

    period_start = _parse_date(data.get("period_start"))
    period_end = _parse_date(data.get("period_end"))
    ref = data.get("reference", f"paystack_inv_{sub_code}")
    amount = data.get("amount", 0)

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(pk=sub.pk)
        if period_end:
            sub.current_period_end = period_end
        if period_start:
            sub.current_period_start = period_start
        sub.status = Subscription.STATUS_ACTIVE
        sub.cancel_at_period_end = False
        sub.save(update_fields=[
            "current_period_start", "current_period_end", "status", "cancel_at_period_end", "updated_at",
        ])

    Invoice.objects.update_or_create(
        paystack_ref=ref,
        defaults={
            "account": sub.account,
            "subscription": sub,
            "amount_kobo": amount,
            "currency": data.get("currency", "GHS"),
            "status": Invoice.STATUS_PAID,
            "period_start": period_start,
            "period_end": period_end,
            "paid_at": datetime.now(dt_timezone.utc),
        },
    )

    AuditService.record_event(
        event_type="payment.invoice_paid",
        entity_type="subscription",
        entity_id=str(sub.pk),
        metadata={"sub_code": sub_code, "period_end": str(period_end)},
    )


def _handle_subscription_expiring_cards(data: dict) -> None:
    """
    Paystack has flagged that the card on file is expiring soon.
    Notify the user to update their payment method.
    """
    customer = data.get("customer") or {}
    sub = _find_subscription_by_email(customer.get("email", ""))
    if not sub:
        logger.info(
            "subscription.expiring_cards: no Subscription for email=%s",
            customer.get("email"),
        )
        return

    _notify(
        sub.account,
        "Your payment card on file is expiring soon. "
        "Please update your card to avoid interruption to your Kotoku subscription.",
    )


# ── Event dispatch table ──────────────────────────────────────────────────────

_HANDLERS = {
    "charge.success":                _handle_charge_success,
    "subscription.create":           _handle_subscription_create,
    "subscription.disable":          _handle_subscription_disable,
    "invoice.payment_failed":        _handle_invoice_payment_failed,
    "invoice.update":                _handle_invoice_update,
    "subscription.expiring_cards":   _handle_subscription_expiring_cards,
}


# ── Celery tasks ──────────────────────────────────────────────────────────────


@shared_task(name="apps.payments.tasks.expire_lapsed_subscriptions")
def expire_lapsed_subscriptions() -> None:
    """
    Daily beat task — downgrade accounts whose subscription has lapsed.

    Targets subscriptions with status cancelled or past_due whose
    current_period_end has passed. Sets:
      - Subscription.status = expired
      - Account.plan = personal_basic

    Idempotent: already-expired subscriptions are skipped on re-runs.
    Writes an AuditLog entry for each downgrade.
    """
    from django.utils import timezone

    today = timezone.now().date()

    lapsed = Subscription.objects.filter(
        status__in=[Subscription.STATUS_CANCELLED, Subscription.STATUS_PAST_DUE],
        current_period_end__lt=today,
    ).select_related("account")

    downgraded = 0
    for sub in lapsed:
        account = sub.account
        old_plan = account.plan
        try:
            with transaction.atomic():
                # Re-fetch under lock — guards against concurrent beat runs.
                sub = Subscription.objects.select_for_update().get(
                    pk=sub.pk,
                    status__in=[Subscription.STATUS_CANCELLED, Subscription.STATUS_PAST_DUE],
                )
                sub.status = Subscription.STATUS_EXPIRED
                sub.save(update_fields=["status", "updated_at"])

                account = sub.account
                if account.plan != "personal_basic":
                    account.plan = "personal_basic"
                    account.save(update_fields=["plan", "updated_at"])

            AuditService.record_event(
                event_type="payment.plan_downgraded",
                entity_type="account",
                entity_id=str(account.pk),
                metadata={
                    "previous_plan": old_plan,
                    "new_plan": "personal_basic",
                    "subscription_id": sub.pk,
                    "period_end": str(sub.current_period_end),
                },
            )
            _notify(
                account,
                "Your Kotoku subscription has ended. "
                "You have been moved to the Personal Basic plan. "
                "Resubscribe anytime to restore your previous limits.",
            )
            _notify_email(
                account,
                subject="Your Kotoku subscription has ended",
                body=(
                    f"Hi {account.full_name or 'there'},\n\n"
                    f"Your Kotoku subscription ({old_plan.replace('_', ' ').title()}) has ended "
                    "and you have been moved to the Personal Basic plan.\n\n"
                    "You can resubscribe at any time from the app to restore your previous limits.\n\n"
                    "The Kotoku team"
                ),
            )
            downgraded += 1
        except Subscription.DoesNotExist:
            # Another concurrent run already processed this subscription — fine.
            continue
        except Exception:
            logger.exception(
                "expire_lapsed_subscriptions: failed to expire sub=%s account=%s",
                sub.pk, account.pk,
            )

    logger.info("expire_lapsed_subscriptions: downgraded %d account(s)", downgraded)


@shared_task(name="apps.payments.tasks.process_payment_event", bind=True, max_retries=0)
def process_payment_event(self, event_id: str) -> None:
    """
    Process a single Paystack webhook event.

    Always re-fetches the PaymentEvent from DB — never trusts data passed through args.
    Sets PaymentEvent.processed=True on success, PaymentEvent.error on failure.
    Does not retry automatically (Paystack retries are handled by re-delivery of the webhook).
    """
    try:
        event = PaymentEvent.objects.get(event_id=event_id)
    except PaymentEvent.DoesNotExist:
        logger.error("process_payment_event: event_id=%s not found in DB", event_id)
        return

    if event.processed:
        logger.info("process_payment_event: event_id=%s already processed — skipping", event_id)
        return

    handler = _HANDLERS.get(event.event_type)
    if not handler:
        logger.info("process_payment_event: no handler for event_type=%s", event.event_type)
        # Mark processed so we don't retry unknown events on every webhook replay.
        PaymentEvent.objects.filter(event_id=event_id).update(processed=True)
        return

    try:
        handler(event.payload.get("data") or {})
        PaymentEvent.objects.filter(event_id=event_id).update(processed=True, error="")
        logger.info(
            "process_payment_event: event_id=%s type=%s processed OK",
            event_id, event.event_type,
        )
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.exception(
            "process_payment_event: event_id=%s type=%s failed: %s",
            event_id, event.event_type, error_msg,
        )
        PaymentEvent.objects.filter(event_id=event_id).update(error=error_msg)
        # Do not re-raise — Paystack will re-deliver the webhook if we return non-2xx,
        # but the webhook view already returned 200. Manual retry via admin if needed.
