from apps.payments.models import Subscription, SubscriptionCheckout


def get_subscription_for_account(account) -> Subscription | None:
    """
    Return the account's current provider subscription row, if one exists.

    The current row is the most recent non-replaced subscription in one of the
    lifecycle states that still represent the user's effective paid access.
    """
    return (
        Subscription.objects.filter(
            account=account,
            status__in=Subscription.CURRENT_STATUSES,
        )
        .order_by("-created_at", "-id")
        .first()
    )


def get_active_subscription(account) -> Subscription | None:
    """Return the subscription only if it is currently active."""
    sub = get_subscription_for_account(account)
    if sub and sub.status == Subscription.STATUS_ACTIVE:
        return sub
    return None


def get_open_checkout_for_account(account) -> SubscriptionCheckout | None:
    """Return the latest open checkout for the account, if one exists."""
    return (
        SubscriptionCheckout.objects.filter(
            account=account,
            status__in=SubscriptionCheckout.OPEN_STATUSES,
        )
        .order_by("-created_at", "-id")
        .first()
    )


def get_checkout_by_reference(reference: str) -> SubscriptionCheckout | None:
    """Return the checkout for the Paystack transaction reference."""
    return SubscriptionCheckout.objects.filter(reference=reference).first()


def get_subscription_status(account) -> dict:
    """
    Return the subscription state dict served by GET /api/payments/subscription/.
    Always returns a dict — has_subscription=False when no subscription exists.
    """
    sub = get_subscription_for_account(account)
    if sub:
        return {
            "has_subscription": True,
            "plan_id": sub.plan_id,
            "status": sub.status,
            "current_period_end": (
                sub.current_period_end.isoformat() if sub.current_period_end else None
            ),
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    checkout = get_open_checkout_for_account(account)
    if checkout:
        return {
            "has_subscription": True,
            "plan_id": checkout.target_plan_id,
            "status": Subscription.STATUS_PENDING,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
    return {"has_subscription": False}
