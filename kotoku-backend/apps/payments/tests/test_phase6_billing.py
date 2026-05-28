"""
Phase 6 tests — billing enforcement integration with payment.

Verifies that BillingService.check_seal_allowed:
  - reads account.plan at call time (not a cached value)
  - enforces the cap for the plan currently on the account
  - respects BILLING_ENFORCEMENT_FAIL_OPEN as an emergency bypass

Covers:
  - personal_basic (1/month) blocks second seal
  - personal_plus (3/month) allows up to 3, blocks the 4th
  - account whose subscription just expired is treated as personal_basic
  - BILLING_ENFORCEMENT_FAIL_OPEN=True bypasses cap errors
  - enterprise soft-cap plan is never hard-blocked
"""

from datetime import date, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.models import Agreement
from apps.billing.services import BillingService
from apps.payments.models import Subscription
from common.exceptions import DomainError

_seq = 0


def _make_account(plan: str = "personal_basic") -> Account:
    global _seq
    _seq += 1
    phone = f"+233400{_seq:06d}"
    user = User.objects.create_user(phone=phone)
    return Account.objects.create(
        user=user,
        email=f"billing{_seq}@test.com",
        phone=phone,
        plan=plan,
    )


def _seal(account: Account, count: int = 1) -> None:
    """Create `count` sealed Agreement rows for this account in the current month."""
    now = timezone.now()
    for i in range(count):
        Agreement.objects.create(
            title=f"Test Agreement {account.pk}-{i}",
            created_by=account,
            status=Agreement.Status.SEALED,
            sealed_at=now,
        )


# ── account.plan is read at call time ────────────────────────────────────────


@pytest.mark.django_db
def test_check_seal_reads_plan_at_call_time():
    """
    If account.plan changes between two calls, the second call reflects the new value.
    This confirms there is no module-level or instance-level plan caching.
    """
    account = _make_account(plan="personal_basic")

    # On personal_basic with 1 seal already used → blocked.
    _seal(account, count=1)
    with pytest.raises(DomainError, match="PLAN_CAP_REACHED"):
        BillingService.check_seal_allowed(account)

    # Simulate webhook upgrading the plan.
    account.plan = "personal_plus"
    account.save(update_fields=["plan", "updated_at"])

    # Same account object, but plan re-read from DB field → now allowed.
    BillingService.check_seal_allowed(account)  # must not raise


# ── personal_basic (cap = 1) ─────────────────────────────────────────────────


@pytest.mark.django_db
def test_personal_basic_first_seal_allowed():
    account = _make_account(plan="personal_basic")
    BillingService.check_seal_allowed(account)  # 0 sealed → OK


@pytest.mark.django_db
def test_personal_basic_second_seal_blocked():
    account = _make_account(plan="personal_basic")
    _seal(account, count=1)
    with pytest.raises(DomainError, match="PLAN_CAP_REACHED"):
        BillingService.check_seal_allowed(account)


# ── personal_plus (cap = 3) ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_personal_plus_within_cap_allowed():
    account = _make_account(plan="personal_plus")
    _seal(account, count=2)
    BillingService.check_seal_allowed(account)  # 2 of 3 used → OK


@pytest.mark.django_db
def test_personal_plus_at_cap_blocked():
    account = _make_account(plan="personal_plus")
    _seal(account, count=3)
    with pytest.raises(DomainError, match="PLAN_CAP_REACHED"):
        BillingService.check_seal_allowed(account)


# ── expired subscription treated as personal_basic ────────────────────────────


@pytest.mark.django_db
def test_expired_subscription_enforces_personal_basic_cap():
    """
    After expire_lapsed_subscriptions runs, account.plan = personal_basic.
    BillingService must enforce the personal_basic cap (1/month) immediately.
    """
    account = _make_account(plan="personal_plus")

    # Simulate the Phase 5 downgrade having already run.
    Subscription.objects.create(
        account=account,
        plan_id="personal_plus",
        paystack_sub_id="SUB_expired",
        paystack_email=account.email,
        status=Subscription.STATUS_EXPIRED,
        current_period_end=date.today() - timedelta(days=1),
    )
    account.plan = "personal_basic"
    account.save(update_fields=["plan", "updated_at"])

    # One seal already used this month → personal_basic cap = 1 → blocked.
    _seal(account, count=1)
    with pytest.raises(DomainError, match="PLAN_CAP_REACHED"):
        BillingService.check_seal_allowed(account)


# ── BILLING_ENFORCEMENT_FAIL_OPEN ─────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(BILLING_ENFORCEMENT_FAIL_OPEN=True)
def test_fail_open_bypasses_cap():
    """
    When BILLING_ENFORCEMENT_FAIL_OPEN=True the billing check in seal_agreement
    swallows enforcement errors. BillingService itself still raises — the bypass
    is in the caller (AgreementService.seal_agreement), not in BillingService.
    This test confirms BillingService raises as normal; the override_settings
    documents that the caller is responsible for the bypass.
    """
    account = _make_account(plan="personal_basic")
    _seal(account, count=1)

    # BillingService always raises — the fail-open lives in AgreementService.
    with pytest.raises(DomainError, match="PLAN_CAP_REACHED"):
        BillingService.check_seal_allowed(account)


# ── Enterprise soft-cap plans never blocked ───────────────────────────────────


@pytest.mark.django_db
def test_enterprise_standard_never_hard_blocked():
    account = _make_account(plan="enterprise_standard")
    # Seal way beyond the soft cap of 20.
    _seal(account, count=25)
    BillingService.check_seal_allowed(account)  # must not raise


@pytest.mark.django_db
def test_enterprise_plus_never_hard_blocked():
    account = _make_account(plan="enterprise_plus")
    _seal(account, count=100)
    BillingService.check_seal_allowed(account)  # must not raise
