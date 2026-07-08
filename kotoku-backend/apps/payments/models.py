import uuid

from django.db import models


def _default_kotoku_ref() -> str:
    return f"kotoku_{uuid.uuid4().hex}"


class Subscription(models.Model):
    """
    One Paystack subscription contract over its lifetime.

    Accounts may have multiple Subscription rows over time as plans are upgraded,
    replaced, cancelled, and expired. Account.plan remains a denormalized projection
    of the current verified plan and is only updated by webhook-driven task logic.
    """

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_CANCELLED = "cancelled"
    STATUS_PAST_DUE = "past_due"
    STATUS_EXPIRED = "expired"
    STATUS_REPLACED = "replaced"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_REPLACED, "Replaced"),
    ]

    CURRENT_STATUSES = [STATUS_ACTIVE, STATUS_PAST_DUE, STATUS_CANCELLED]

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    # Paystack identifiers — blank until confirmed by webhook
    paystack_sub_id = models.CharField(max_length=100, blank=True, db_index=True)
    paystack_customer_code = models.CharField(max_length=100, blank=True)
    paystack_email = models.EmailField()
    paystack_plan_code = models.CharField(max_length=100, blank=True)

    # Mirrors billing.constants.PLAN_MAP key
    plan_id = models.CharField(max_length=32)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    current_period_start = models.DateField(null=True, blank=True)
    current_period_end = models.DateField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    replaced_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_subscriptions"
        indexes = [
            models.Index(fields=["account", "status"]),
            models.Index(fields=["status", "current_period_end"]),
        ]

    def __str__(self) -> str:
        return f"Subscription({self.account_id} / {self.plan_id} / {self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE


class SubscriptionCheckout(models.Model):
    """
    One initiated checkout flow, keyed by the Paystack transaction reference.

    This is the authoritative pending state for new purchases and plan switches.
    It prevents the current active provider subscription row from being reused
    as the target state of a new checkout.
    """

    STATUS_PENDING = "pending"
    STATUS_CHARGED = "charged"
    STATUS_PROVIDER_CREATED = "provider_created"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_SUPERSEDED = "superseded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CHARGED, "Charged"),
        (STATUS_PROVIDER_CREATED, "Provider created"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SUPERSEDED, "Superseded"),
    ]

    OPEN_STATUSES = [STATUS_PENDING, STATUS_CHARGED]

    KIND_SUBSCRIPTION = "subscription"
    KIND_RECOVERY = "recovery"

    KIND_CHOICES = [
        (KIND_SUBSCRIPTION, "Subscription"),
        (KIND_RECOVERY, "Recovery"),
    ]

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="subscription_checkouts",
    )
    reference = models.CharField(max_length=255, unique=True)
    target_plan_id = models.CharField(max_length=32)
    checkout_kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_SUBSCRIPTION,
        db_index=True,
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    replaces_subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_checkouts",
    )
    activated_subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activation_checkouts",
    )
    recovery_subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recovery_checkouts",
    )
    authorization_url = models.TextField(blank=True)
    access_code = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_subscription_checkouts"
        indexes = [
            models.Index(fields=["account", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"SubscriptionCheckout({self.account_id} / {self.target_plan_id} / "
            f"{self.checkout_kind} / {self.status})"
        )


class PaymentEvent(models.Model):
    """
    Append-only log of every Paystack webhook event received.
    event_id is the Paystack event ID used for idempotency — never process the same event twice.
    Processing is always delegated to a Celery task; the webhook view only records and dispatches.
    """

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False, db_index=True)
    # Set when the Celery task raises an exception during processing
    error = models.TextField(blank=True)

    class Meta:
        db_table = "payment_events"
        indexes = [
            models.Index(fields=["received_at"]),
        ]
        # Prevent any update/delete at the model layer by convention — never call .delete()
        # or bulk_update on this model. Treated as append-only like AuditLog.

    def __str__(self) -> str:
        return f"PaymentEvent({self.event_type} / {self.event_id})"


class Invoice(models.Model):
    """
    Record of each billing cycle charge.
    Populated from Paystack invoice.update and charge.success events.
    """

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
    ]

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    paystack_ref = models.CharField(max_length=255, unique=True)
    # Paystack amounts are in the smallest currency unit (kobo for GHS)
    amount_kobo = models.IntegerField()
    currency = models.CharField(max_length=10, default="GHS")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payment_invoices"
        indexes = [
            models.Index(fields=["account", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Invoice({self.paystack_ref} / {self.status})"
