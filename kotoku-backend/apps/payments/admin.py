from django.contrib import admin
from django.utils.html import format_html

from apps.payments.models import Invoice, PaymentEvent, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "account_link", "plan_id", "status_badge", "current_period_end", "cancel_at_period_end", "created_at")
    list_filter = ("status", "plan_id")
    search_fields = ("account__email", "account__phone", "paystack_sub_id", "paystack_customer_code")
    ordering = ("-created_at",)
    readonly_fields = (
        "account", "paystack_sub_id", "paystack_customer_code", "paystack_email",
        "paystack_plan_code", "plan_id", "status", "current_period_start",
        "current_period_end", "cancel_at_period_end", "created_at", "updated_at",
    )

    _STATUS_STYLES = {
        "pending":   "background:#F3F4F6;color:#374151",
        "active":    "background:#D1FAE5;color:#065F46",
        "paused":    "background:#DBEAFE;color:#1E40AF",
        "cancelled": "background:#FEE2E2;color:#991B1B",
        "past_due":  "background:#FEF3C7;color:#92400E",
        "expired":   "background:#F3F4F6;color:#6B7280",
    }

    def status_badge(self, obj: Subscription) -> str:
        style = self._STATUS_STYLES.get(obj.status, "")
        return format_html(
            '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
            style,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"  # type: ignore[attr-defined]
    status_badge.admin_order_field = "status"  # type: ignore[attr-defined]

    def account_link(self, obj: Subscription) -> str:
        url = f"/admin/accounts/account/{obj.account_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.account)
    account_link.short_description = "Account"  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "event_id", "processed", "received_at", "has_error")
    list_filter = ("event_type", "processed")
    search_fields = ("event_id", "event_type")
    ordering = ("-received_at",)
    readonly_fields = ("event_id", "event_type", "payload", "received_at", "processed", "error")

    def has_error(self, obj: PaymentEvent) -> bool:
        return bool(obj.error)
    has_error.short_description = "Error"  # type: ignore[attr-defined]
    has_error.boolean = True  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "account_link", "paystack_ref", "amount_ghs", "status", "period_end", "paid_at", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("account__email", "paystack_ref")
    ordering = ("-created_at",)
    readonly_fields = (
        "account", "subscription", "paystack_ref", "amount_kobo",
        "currency", "status", "period_start", "period_end", "paid_at", "created_at",
    )

    def amount_ghs(self, obj: Invoice) -> str:
        return f"GHS {obj.amount_kobo / 100:.2f}"
    amount_ghs.short_description = "Amount"  # type: ignore[attr-defined]

    def account_link(self, obj: Invoice) -> str:
        url = f"/admin/accounts/account/{obj.account_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.account)
    account_link.short_description = "Account"  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
