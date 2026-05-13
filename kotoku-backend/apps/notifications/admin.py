from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html

from apps.notifications.providers.sms_provider import SmsNotificationProvider

from .models import Notification


# ── Badges ───────────────────────────────────────────────────────────────────

_STATUS_STYLES = {
    "pending": "background:#FEF3C7;color:#92400E",
    "sent":    "background:#D1FAE5;color:#065F46",
    "failed":  "background:#FEE2E2;color:#991B1B",
}

_CHANNEL_STYLES = {
    "sms":      "background:#EDE9FE;color:#5B21B6",
    "whatsapp": "background:#D1FAE5;color:#065F46",
    "in_app":   "background:#DBEAFE;color:#1E40AF",
}


def coloured_status(obj: Notification) -> str:
    style = _STATUS_STYLES.get(obj.status, "")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style,
        obj.get_status_display(),
    )
coloured_status.short_description = "Status"  # type: ignore[attr-defined]


def coloured_channel(obj: Notification) -> str:
    style = _CHANNEL_STYLES.get(obj.channel, "")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style,
        obj.get_channel_display(),
    )
coloured_channel.short_description = "Channel"  # type: ignore[attr-defined]


def body_preview(obj: Notification) -> str:
    return obj.body[:80] + ("…" if len(obj.body) > 80 else "")
body_preview.short_description = "Message preview"  # type: ignore[attr-defined]


# ── Bulk action ───────────────────────────────────────────────────────────────

_PROVIDERS = {
    Notification.Channel.SMS: SmsNotificationProvider,
}


@admin.action(description="Retry sending failed notifications")
def action_retry_failed(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    retried = 0
    errors = 0
    for notif in queryset.filter(status=Notification.Status.FAILED).select_related("account"):
        provider_cls = _PROVIDERS.get(notif.channel)
        if provider_cls is None:
            errors += 1
            continue
        destination = notif.account.phone
        try:
            success = provider_cls().send(to=destination, body=notif.body)
            if success:
                notif.status = Notification.Status.SENT
                notif.sent_at = timezone.now()
                notif.save(update_fields=["status", "sent_at"])
                retried += 1
            else:
                errors += 1
        except Exception:
            errors += 1

    msg = f"Resent {retried} notification(s)."
    if errors:
        msg += f" {errors} could not be sent."
    level = messages.SUCCESS if not errors else messages.WARNING
    modeladmin.message_user(request, msg, level)


# ── Admin class ───────────────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    # ── List view ─────────────────────────────────────────────────────────────
    list_display = (
        "id", "account_link", coloured_channel, coloured_status,
        body_preview, "sent_at", "created_at",
    )
    list_select_related = ("account",)
    list_filter = ("channel", "status", "created_at")
    search_fields = ("body", "account__email", "account__full_name", "account__phone")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = [action_retry_failed]

    # ── Detail view ───────────────────────────────────────────────────────────
    readonly_fields = (
        "account_link",
        coloured_channel,
        coloured_status,
        "body",
        "sent_at",
        "created_at",
    )
    fieldsets = (
        ("Recipient", {
            "fields": ("account_link", coloured_channel, coloured_status, "sent_at", "created_at"),
        }),
        ("Message body", {
            "fields": ("body",),
        }),
    )

    def account_link(self, obj: Notification) -> str:
        url = f"/admin/accounts/account/{obj.account_id}/change/"
        label = obj.account.full_name or obj.account.email
        return format_html('<a href="{}">{}</a>', url, label)
    account_link.short_description = "Account"  # type: ignore[attr-defined]
