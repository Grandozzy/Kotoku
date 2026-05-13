from datetime import date, timedelta

from django.db.models import Count
from django.utils import timezone

from apps.billing.constants import (
    MISUSE_CONSECUTIVE_MONTHS_AT_CAP,
    MISUSE_ROLLING_90_DAY_AGREEMENTS,
    get_plan,
    get_recommended_upgrades,
)


def _month_window(today: date) -> tuple[date, date]:
    """Return (first_day, last_day) of the current calendar month."""
    first = today.replace(day=1)
    if today.month == 12:
        last = today.replace(day=31)
    else:
        last = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first, last


def _sealed_in_window(account, start: date, end: date) -> int:
    from apps.agreements.models import Agreement  # avoid circular import

    return Agreement.objects.filter(
        created_by=account,
        status="sealed",
        sealed_at__date__gte=start,
        sealed_at__date__lte=end,
    ).count()


def _check_business_misuse(account, plan) -> bool:
    """Return True if heuristics suggest Personal account is using Kotoku as a business."""
    if plan.family != "personal":
        return False

    today = timezone.now().date()

    # Heuristic 1: sealed >15 agreements in rolling 90 days
    rolling_start = today - timedelta(days=90)
    rolling_count = _sealed_in_window(account, rolling_start, today)
    if rolling_count >= MISUSE_ROLLING_90_DAY_AGREEMENTS:
        return True

    # Heuristic 2: hit cap in 3 consecutive calendar months
    months_at_cap = 0
    check_date = today
    for _ in range(MISUSE_CONSECUTIVE_MONTHS_AT_CAP):
        first, last = _month_window(check_date)
        count = _sealed_in_window(account, first, last)
        if count >= plan.max_agreements_per_month:
            months_at_cap += 1
        else:
            break
        # Move back one month
        check_date = first - timedelta(days=1)

    if months_at_cap >= MISUSE_CONSECUTIVE_MONTHS_AT_CAP:
        return True

    return False


def get_current_plan_usage(account) -> dict:
    """
    Return the full billing context for one account:
    plan metadata, current-month usage, flags, and upgrade recommendations.
    This is the data shape returned by GET /api/billing/current-plan/.
    """
    plan = get_plan(account.plan)
    today = timezone.now().date()
    period_start, period_end = _month_window(today)

    sealed_this_period = _sealed_in_window(account, period_start, period_end)
    remaining = max(plan.max_agreements_per_month - sealed_this_period, 0)
    is_cap_reached = sealed_this_period >= plan.max_agreements_per_month
    # Near cap: ≥80% used (but not for soft-cap Enterprise plans)
    is_near_cap = (
        not plan.is_soft_cap
        and not is_cap_reached
        and plan.max_agreements_per_month > 0
        and (sealed_this_period / plan.max_agreements_per_month) >= 0.8
    )

    business_misuse = _check_business_misuse(account, plan)
    show_upgrade = (
        (is_cap_reached and plan.family == "personal")
        or business_misuse
    )

    recommended = get_recommended_upgrades(plan)

    return {
        "plan": {
            "id": plan.id,
            "family": plan.family,
            "name": plan.name,
            "price_currency": "GHS",
            "price_amount_monthly": plan.price_ghs,
            "max_agreements_per_month": plan.max_agreements_per_month,
            "retention_months": plan.retention_months,
            "features": {
                "team_seats": plan.features.team_seats,
                "bulk_creation": plan.features.bulk_creation,
                "reporting": plan.features.reporting,
                "archive_search": plan.features.archive_search,
            },
        },
        "usage": {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "sealed_agreements_this_period": sealed_this_period,
            "remaining_agreements_this_period": remaining,
            "is_cap_reached": is_cap_reached,
            "is_near_cap": is_near_cap,
        },
        "flags": {
            "is_personal": plan.family == "personal",
            "is_enterprise": plan.family == "enterprise",
            "business_usage_suspected": business_misuse,
            "show_upgrade_recommendation": show_upgrade,
        },
        "recommended_upgrades": [
            {
                "id": p.id,
                "name": p.name,
                "family": p.family,
                "price_currency": "GHS",
                "price_amount_monthly": p.price_ghs,
                "max_agreements_per_month": p.max_agreements_per_month,
            }
            for p in recommended
        ],
    }
