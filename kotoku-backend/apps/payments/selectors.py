from apps.payments.models import Subscription


def get_subscription_for_account(account) -> Subscription | None:
    """Return the account's subscription row, or None if it does not exist."""
    try:
        return account.subscription
    except Subscription.DoesNotExist:
        return None


def get_active_subscription(account) -> Subscription | None:
    """Return the subscription only if it is currently active."""
    sub = get_subscription_for_account(account)
    if sub and sub.status == Subscription.STATUS_ACTIVE:
        return sub
    return None


def get_subscription_status(account) -> dict:
    """
    Return the subscription state dict served by GET /api/payments/subscription/.
    Always returns a dict — has_subscription=False when no subscription exists.
    """
    sub = get_subscription_for_account(account)
    if not sub:
        return {"has_subscription": False}
    return {
        "has_subscription": True,
        "plan_id": sub.plan_id,
        "status": sub.status,
        "current_period_end": (
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
        "cancel_at_period_end": sub.cancel_at_period_end,
    }
