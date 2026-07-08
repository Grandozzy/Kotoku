import logging
import uuid
from calendar import monthrange
from datetime import date, datetime
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import transaction

from apps.audit.services import AuditService
from apps.billing.constants import PLAN_MAP
from apps.notifications.models import Notification
from apps.payments.models import Invoice, Subscription, SubscriptionCheckout
from apps.payments.selectors import get_open_checkout_for_account, get_subscription_for_account
from common.exceptions import DomainError
from infrastructure.paystack.client import InitializeResult, PaystackError, get_paystack_client

logger = logging.getLogger("kotoku")


class PaymentService:
    @staticmethod
    def _notify(account, body: str) -> None:
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_notification(
                account_id=account.pk,
                channel=Notification.Channel.SMS,
                body=body,
            )
        except Exception:
            logger.exception("Failed to send payment SMS notification to account=%s", account.pk)

    @staticmethod
    def _notify_email(account, *, subject: str, body: str) -> None:
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

    @staticmethod
    def _add_one_month(value: date) -> date:
        month = value.month + 1
        year = value.year
        if month > 12:
            month = 1
            year += 1
        day = min(value.day, monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def _create_checkout(
        *,
        account,
        plan_id: str,
        authorization_url: str,
        access_code: str,
        reference: str,
        checkout_kind: str,
        replaces_subscription=None,
        recovery_subscription=None,
    ) -> None:
        SubscriptionCheckout.objects.create(
            account=account,
            reference=reference,
            target_plan_id=plan_id,
            checkout_kind=checkout_kind,
            status=SubscriptionCheckout.STATUS_PENDING,
            replaces_subscription=replaces_subscription,
            recovery_subscription=recovery_subscription,
            authorization_url=authorization_url,
            access_code=access_code,
        )

    @staticmethod
    def _reconcile_recovery_checkout(data: dict, checkout: SubscriptionCheckout) -> dict | None:
        if checkout.checkout_kind != SubscriptionCheckout.KIND_RECOVERY:
            return None

        customer = data.get("customer") or {}
        customer_code = customer.get("customer_code", "")
        customer_email = customer.get("email", "")
        reference = data.get("reference", "")
        amount = data.get("amount", 0)
        currency = data.get("currency", "GHS")

        with transaction.atomic():
            locked_checkout = (
                SubscriptionCheckout.objects.select_for_update()
                .select_related("account", "recovery_subscription", "activated_subscription")
                .get(pk=checkout.pk)
            )
            sub = locked_checkout.recovery_subscription
            if not sub:
                logger.error(
                    "recovery charge.success missing recovery_subscription for checkout=%s",
                    checkout.pk,
                )
                return None

            sub = Subscription.objects.select_for_update().get(pk=sub.pk)
            account = locked_checkout.account
            already_reconciled = (
                locked_checkout.status == SubscriptionCheckout.STATUS_PROVIDER_CREATED
                and locked_checkout.activated_subscription_id == sub.pk
                and sub.status == Subscription.STATUS_ACTIVE
                and account.plan == sub.plan_id
            )
            if already_reconciled:
                return {
                    "changed": False,
                    "account": account,
                    "subscription": sub,
                    "checkout": locked_checkout,
                }

            base_period_end = sub.current_period_end or date.today()
            next_period_end = PaymentService._add_one_month(base_period_end)
            sub.current_period_start = base_period_end
            sub.current_period_end = next_period_end
            sub.status = Subscription.STATUS_ACTIVE
            sub.cancel_at_period_end = False
            if customer_code:
                sub.paystack_customer_code = customer_code
            if customer_email:
                sub.paystack_email = customer_email
            sub.save(update_fields=[
                "current_period_start",
                "current_period_end",
                "status",
                "cancel_at_period_end",
                "paystack_customer_code",
                "paystack_email",
                "updated_at",
            ])

            locked_checkout.status = SubscriptionCheckout.STATUS_PROVIDER_CREATED
            locked_checkout.activated_subscription = sub
            locked_checkout.save(update_fields=["status", "activated_subscription", "updated_at"])

            if account.plan != sub.plan_id:
                account.plan = sub.plan_id
                account.save(update_fields=["plan", "updated_at"])

        Invoice.objects.update_or_create(
            paystack_ref=reference or f"paystack_recovery_{checkout.pk}",
            defaults={
                "account": account,
                "subscription": sub,
                "amount_kobo": amount,
                "currency": currency,
                "status": Invoice.STATUS_PAID,
                "period_start": sub.current_period_start,
                "period_end": sub.current_period_end,
                "paid_at": datetime.now(dt_timezone.utc),
            },
        )

        AuditService.record_event(
            event_type="payment.recovery_paid",
            entity_type="subscription",
            entity_id=str(sub.pk),
            actor=f"paystack:{customer_code or sub.paystack_customer_code}",
            metadata={"reference": reference, "plan_id": sub.plan_id},
        )
        plan_name = sub.plan_id.replace("_", " ").title()
        PaymentService._notify(account, f"Your Kotoku {plan_name} subscription is active again.")
        PaymentService._notify_email(
            account,
            subject=f"Your Kotoku {plan_name} subscription is active again",
            body=(
                f"Hi {account.full_name or 'there'},\n\n"
                f"Your recovery payment for Kotoku {plan_name} was successful.\n\n"
                "Your subscription is active again.\n\n"
                "The Kotoku team"
            ),
        )
        return {
            "changed": True,
            "account": account,
            "subscription": sub,
            "checkout": locked_checkout,
        }

    @staticmethod
    def reconcile_verified_charge(data: dict) -> dict | None:
        reference = data.get("reference", "")
        plan_info = data.get("plan") or {}
        checkout = (
            SubscriptionCheckout.objects.select_related("account", "activated_subscription", "recovery_subscription")
            .filter(reference=reference)
            .first()
            if reference
            else None
        )

        if not plan_info:
            if checkout:
                return PaymentService._reconcile_recovery_checkout(data, checkout)
            logger.info("charge.success has no plan and no recovery checkout — skipping")
            return None

        metadata = data.get("metadata") or {}
        account_id = metadata.get("account_id")
        plan_id = metadata.get("plan_id")
        if checkout:
            account_id = checkout.account_id
            plan_id = checkout.target_plan_id
        if not account_id or not plan_id:
            logger.error("charge.success missing account_id/plan_id in metadata: %s", metadata)
            return None

        customer = data.get("customer") or {}
        customer_code = customer.get("customer_code", "")
        customer_email = customer.get("email", "")

        from apps.accounts.models import Account
        try:
            account = Account.objects.get(pk=account_id)
        except Account.DoesNotExist:
            logger.error("charge.success: account_id=%s not found", account_id)
            return None

        with transaction.atomic():
            locked_checkout = None
            sub = None
            next_status = Subscription.STATUS_ACTIVE

            if checkout:
                locked_checkout = (
                    SubscriptionCheckout.objects.select_for_update()
                    .select_related("account", "activated_subscription")
                    .get(pk=checkout.pk)
                )
                if (
                    locked_checkout.status in (
                        SubscriptionCheckout.STATUS_CHARGED,
                        SubscriptionCheckout.STATUS_PROVIDER_CREATED,
                    )
                    and locked_checkout.activated_subscription_id
                    and account.plan == plan_id
                ):
                    sub = Subscription.objects.select_for_update().get(
                        pk=locked_checkout.activated_subscription_id
                    )
                    return {
                        "changed": False,
                        "account": account,
                        "subscription": sub,
                        "checkout": locked_checkout,
                    }
                if locked_checkout.replaces_subscription_id:
                    next_status = Subscription.STATUS_PENDING
                if locked_checkout.activated_subscription_id:
                    sub = Subscription.objects.select_for_update().get(
                        pk=locked_checkout.activated_subscription_id
                    )

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
        PaymentService._notify(account, f"Your Kotoku {plan_name} subscription is now active.")
        PaymentService._notify_email(
            account,
            subject=f"Your Kotoku {plan_name} subscription is active",
            body=(
                f"Hi {account.full_name or 'there'},\n\n"
                f"Your Kotoku {plan_name} subscription is now active.\n\n"
                "You can seal agreements up to your plan limit each month.\n\n"
                "The Kotoku team"
            ),
        )
        return {
            "changed": True,
            "account": account,
            "subscription": sub,
            "checkout": locked_checkout,
        }

    @staticmethod
    def get_checkout_status(account, reference: str) -> dict:
        checkout = (
            SubscriptionCheckout.objects.select_related(
                "activated_subscription",
                "recovery_subscription",
            )
            .filter(account=account, reference=reference)
            .first()
        )
        if not checkout:
            raise DomainError("Payment session not found.")

        if checkout.status not in (
            SubscriptionCheckout.STATUS_CANCELLED,
            SubscriptionCheckout.STATUS_FAILED,
        ):
            try:
                verify_data = get_paystack_client().verify_transaction(reference)
            except PaystackError as exc:
                logger.warning("Paystack verify failed for reference=%s: %s", reference, exc)
            else:
                remote_status = str(verify_data.get("status", "")).lower()
                if remote_status == "success":
                    PaymentService.reconcile_verified_charge(verify_data)
                elif remote_status == "abandoned":
                    SubscriptionCheckout.objects.filter(
                        pk=checkout.pk,
                        status__in=(
                            SubscriptionCheckout.STATUS_PENDING,
                            SubscriptionCheckout.STATUS_CHARGED,
                            SubscriptionCheckout.STATUS_PROVIDER_CREATED,
                        ),
                    ).update(status=SubscriptionCheckout.STATUS_CANCELLED)
                elif remote_status in {"failed", "reversed"}:
                    SubscriptionCheckout.objects.filter(
                        pk=checkout.pk,
                        status__in=(
                            SubscriptionCheckout.STATUS_PENDING,
                            SubscriptionCheckout.STATUS_CHARGED,
                            SubscriptionCheckout.STATUS_PROVIDER_CREATED,
                        ),
                    ).update(status=SubscriptionCheckout.STATUS_FAILED)

        checkout.refresh_from_db()
        account.refresh_from_db()

        subscription = checkout.activated_subscription or checkout.recovery_subscription
        if subscription:
            subscription.refresh_from_db()

        checkout_status = "processing"
        detail = "Payment is still being confirmed."

        if checkout.status == SubscriptionCheckout.STATUS_CANCELLED:
            checkout_status = "cancelled"
            detail = "Payment was cancelled before confirmation."
        elif checkout.status == SubscriptionCheckout.STATUS_FAILED:
            checkout_status = "failed"
            detail = "Payment did not complete successfully."
        elif account.plan == checkout.target_plan_id and checkout.status in (
            SubscriptionCheckout.STATUS_CHARGED,
            SubscriptionCheckout.STATUS_PROVIDER_CREATED,
        ):
            checkout_status = "succeeded"
            detail = "Payment confirmed and plan updated."
        elif checkout.status == SubscriptionCheckout.STATUS_PENDING:
            checkout_status = "pending"
            detail = "Waiting for payment confirmation."

        return {
            "reference": checkout.reference,
            "checkout_status": checkout_status,
            "target_plan_id": checkout.target_plan_id,
            "current_plan_id": account.plan,
            "subscription_status": subscription.status if subscription else None,
            "detail": detail,
        }

    @staticmethod
    def initiate_subscription(
        account,
        plan_id: str,
        callback_url: str | None = None,
    ) -> InitializeResult:
        plan = PLAN_MAP.get(plan_id)
        if not plan:
            raise DomainError(f"Invalid plan: {plan_id!r}.")

        plan_code = settings.PAYSTACK_PLAN_CODES.get(plan_id, "")
        if not plan_code:
            raise DomainError(
                f"Online payment is not yet available for {plan.name}. "
                "Please contact support."
            )

        existing = get_subscription_for_account(account)
        if existing and existing.status == Subscription.STATUS_ACTIVE and existing.plan_id == plan_id:
            raise DomainError("You already have an active subscription for this plan.")

        open_checkout = get_open_checkout_for_account(account)
        if open_checkout:
            raise DomainError(
                "A payment session is already in progress for this account. "
                "Please complete it or wait a moment before starting another."
            )

        reference = f"kotoku_{uuid.uuid4().hex}"

        try:
            client = get_paystack_client()
            result = client.initialize_transaction(
                email=account.email,
                amount_kobo=plan.price_ghs * 100,
                plan_code=plan_code,
                reference=reference,
                callback_url=callback_url or getattr(settings, "PAYSTACK_CALLBACK_URL", ""),
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

        with transaction.atomic():
            current = (
                Subscription.objects.select_for_update()
                .filter(account=account, status__in=Subscription.CURRENT_STATUSES)
                .order_by("-created_at", "-id")
                .first()
            )
            if current and current.status == Subscription.STATUS_ACTIVE and current.plan_id == plan_id:
                raise DomainError("You already have an active subscription for this plan.")
            existing_checkout = (
                SubscriptionCheckout.objects.select_for_update()
                .filter(account=account, status__in=SubscriptionCheckout.OPEN_STATUSES)
                .first()
            )
            if existing_checkout:
                raise DomainError(
                    "A payment session is already in progress for this account. "
                    "Please complete it or wait a moment before starting another."
                )
            PaymentService._create_checkout(
                account=account,
                plan_id=plan_id,
                authorization_url=result.authorization_url,
                access_code=result.access_code,
                reference=result.reference,
                checkout_kind=SubscriptionCheckout.KIND_SUBSCRIPTION,
                replaces_subscription=current,
            )

        return result

    @staticmethod
    def initiate_recovery_payment(
        account,
        plan_id: str,
        *,
        callback_url: str | None = None,
        channels: list[str] | None = None,
    ) -> InitializeResult:
        plan = PLAN_MAP.get(plan_id)
        if not plan:
            raise DomainError(f"Invalid plan: {plan_id!r}.")

        open_checkout = get_open_checkout_for_account(account)
        if open_checkout:
            raise DomainError(
                "A payment session is already in progress for this account. "
                "Please complete it or wait a moment before starting another."
            )

        existing = get_subscription_for_account(account)
        if not existing or existing.status != Subscription.STATUS_PAST_DUE:
            raise DomainError("Recovery payment is only available for past-due subscriptions.")
        if existing.plan_id != plan_id:
            raise DomainError("Recovery payment must match your current past-due plan.")

        reference = f"kotoku_{uuid.uuid4().hex}"
        selected_channels = channels or ["card", "mobile_money"]

        try:
            client = get_paystack_client()
            result = client.initialize_transaction(
                email=account.email,
                amount_kobo=plan.price_ghs * 100,
                reference=reference,
                callback_url=callback_url or getattr(settings, "PAYSTACK_CALLBACK_URL", ""),
                metadata={
                    "account_id": account.id,
                    "plan_id": plan_id,
                    "payment_mode": SubscriptionCheckout.KIND_RECOVERY,
                    "subscription_id": existing.id,
                    "kotoku_ref": reference,
                },
                channels=selected_channels,
            )
        except PaystackError as exc:
            logger.error(
                "Paystack recovery initiate failed for account=%s plan=%s: %s",
                account.id, plan_id, exc,
            )
            raise DomainError(
                "Payment gateway error. Please try again or contact support."
            ) from exc

        with transaction.atomic():
            sub = Subscription.objects.select_for_update().get(pk=existing.pk)
            if sub.status != Subscription.STATUS_PAST_DUE:
                raise DomainError("Recovery payment is only available for past-due subscriptions.")
            existing_checkout = (
                SubscriptionCheckout.objects.select_for_update()
                .filter(account=account, status__in=SubscriptionCheckout.OPEN_STATUSES)
                .first()
            )
            if existing_checkout:
                raise DomainError(
                    "A payment session is already in progress for this account. "
                    "Please complete it or wait a moment before starting another."
                )
            PaymentService._create_checkout(
                account=account,
                plan_id=plan_id,
                authorization_url=result.authorization_url,
                access_code=result.access_code,
                reference=result.reference,
                checkout_kind=SubscriptionCheckout.KIND_RECOVERY,
                recovery_subscription=sub,
            )

        return result

    @staticmethod
    def cancel_subscription(account) -> None:
        sub = get_subscription_for_account(account)
        if not sub:
            any_subscription = (
                Subscription.objects.filter(account=account)
                .order_by("-created_at", "-id")
                .first()
            )
            if any_subscription:
                raise DomainError("No active subscription to cancel.")
            raise DomainError("No subscription found.")
        if sub.status != Subscription.STATUS_ACTIVE:
            raise DomainError("No active subscription to cancel.")
        if not sub.paystack_sub_id:
            raise DomainError(
                "Subscription is not yet confirmed by payment provider. "
                "Please try again in a few moments."
            )

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

        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(
                    account=account,
                    status=Subscription.STATUS_ACTIVE,
                )
            except Subscription.DoesNotExist:
                return
            sub.cancel_at_period_end = True
            sub.save(update_fields=["cancel_at_period_end", "updated_at"])
