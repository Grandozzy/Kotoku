from django.utils import timezone

from apps.billing.constants import get_plan
from apps.billing.selectors import _month_window, _sealed_in_window
from common.exceptions import DomainError


class BillingService:
    @staticmethod
    def check_seal_allowed(account) -> None:
        """
        Raise DomainError with code PLAN_CAP_REACHED if the account has
        exhausted their monthly sealing allowance.

        Enterprise soft caps are not hard-blocked — they pass through silently.
        This should be called at the start of AgreementService.seal_agreement().
        """
        plan = get_plan(account.plan)

        # Enterprise plans are soft-capped; never hard-block them.
        if plan.is_soft_cap:
            return

        today = timezone.now().date()
        period_start, period_end = _month_window(today)
        sealed = _sealed_in_window(account, period_start, period_end)

        if sealed >= plan.max_agreements_per_month:
            raise DomainError(
                f"PLAN_CAP_REACHED: You've reached your {plan.max_agreements_per_month} agreement "
                f"limit for this month on {plan.name}. Upgrade to a higher plan or wait until "
                f"next month."
            )
