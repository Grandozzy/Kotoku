import uuid
import logging

from django.conf import settings
from django.db import transaction

from apps.billing.constants import PLAN_MAP
from apps.payments.models import Subscription
from apps.payments.selectors import get_subscription_for_account
from common.exceptions import DomainError
from infrastructure.paystack.client import InitializeResult, PaystackError, get_paystack_client

logger = logging.getLogger("kotoku")


class PaymentService:

    @staticmethod
    def initiate_subscription(account, plan_id: str) -> InitializeResult:
        """
        Begin a Paystack checkout for the given plan.

        Returns an InitializeResult with authorization_url, access_code, and reference.
        The Subscription row is created (or updated) with status=pending.
        Account.plan is NOT changed here — only a verified webhook does that (Phase 4).
        """
        plan = PLAN_MAP.get(plan_id)
        if not plan:
            raise DomainError(f"Invalid plan: {plan_id!r}.")

        plan_code = settings.PAYSTACK_PLAN_CODES.get(plan_id, "")
        if not plan_code:
            raise DomainError(
                f"Online payment is not yet available for {plan.name}. "
                "Please contact support."
            )

        # Advisory check — reconfirmed under lock after Paystack call below.
        existing = get_subscription_for_account(account)
        if existing and existing.status == Subscription.STATUS_ACTIVE and existing.plan_id == plan_id:
            raise DomainError("You already have an active subscription for this plan.")

        reference = f"kotoku_{uuid.uuid4().hex}"

        # Call Paystack outside any DB transaction — never hold a lock during network I/O.
        try:
            client = get_paystack_client()
            result = client.initialize_transaction(
                email=account.email,
                amount_kobo=plan.price_ghs * 100,
                plan_code=plan_code,
                reference=reference,
                callback_url=getattr(settings, "PAYSTACK_CALLBACK_URL", ""),
                metadata={
                    "account_id": account.id,
                    "plan_id": plan_id,
                    "kotoku_ref": reference,
                },
            )
        except PaystackError as exc:
            logger.error(
                "Paystack initiate failed for account=%s plan=%s: %s",
                account.id, plan_id, exc,
            )
            raise DomainError(
                "Payment gateway error. Please try again or contact support."
            ) from exc

        # Persist the pending subscription inside a transaction with a lock.
        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(account=account)
                # Re-check under lock — another request may have activated a subscription
                # between our advisory check and now.
                if sub.status == Subscription.STATUS_ACTIVE and sub.plan_id == plan_id:
                    raise DomainError("You already have an active subscription for this plan.")
                sub.plan_id = plan_id
                sub.paystack_plan_code = plan_code
                sub.paystack_email = account.email
                sub.status = Subscription.STATUS_PENDING
                sub.save(update_fields=[
                    "plan_id", "paystack_plan_code", "paystack_email", "status", "updated_at",
                ])
            except Subscription.DoesNotExist:
                Subscription.objects.create(
                    account=account,
                    plan_id=plan_id,
                    paystack_plan_code=plan_code,
                    paystack_email=account.email,
                    status=Subscription.STATUS_PENDING,
                )

        return result

    @staticmethod
    def cancel_subscription(account) -> None:
        """
        Cancel the account's active subscription at the end of the current billing period.

        Does NOT downgrade Account.plan immediately — the period-end Celery task (Phase 5)
        handles the downgrade once current_period_end passes.
        """
        sub = get_subscription_for_account(account)
        if not sub:
            raise DomainError("No subscription found.")
        if sub.status != Subscription.STATUS_ACTIVE:
            raise DomainError("No active subscription to cancel.")
        if not sub.paystack_sub_id:
            raise DomainError(
                "Subscription is not yet confirmed by payment provider. "
                "Please try again in a few moments."
            )

        # Fetch the email token Paystack requires for cancellation — done outside a transaction.
        try:
            client = get_paystack_client()
            paystack_data = client.fetch_subscription(sub.paystack_sub_id)
            email_token = paystack_data.get("email_token", "")
            if not email_token:
                raise DomainError(
                    "Unable to retrieve cancellation token. Please try again or contact support."
                )
            client.cancel_subscription(
                subscription_code=sub.paystack_sub_id,
                email_token=email_token,
            )
        except PaystackError as exc:
            logger.error(
                "Paystack cancel failed for account=%s sub=%s: %s",
                account.id, sub.paystack_sub_id, exc,
            )
            raise DomainError(
                "Payment gateway error while cancelling. Please try again or contact support."
            ) from exc

        # Mark cancel_at_period_end under a lock — idempotent if called twice.
        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(
                    account=account,
                    status=Subscription.STATUS_ACTIVE,
                )
            except Subscription.DoesNotExist:
                # Another request already cancelled — safe to return silently.
                return
            sub.cancel_at_period_end = True
            sub.save(update_fields=["cancel_at_period_end", "updated_at"])
