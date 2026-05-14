from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.billing.constants import PLANS, get_plan

from .models import Account, DeviceSession, User


# ── Plan badge ────────────────────────────────────────────────────────────────

_PLAN_STYLES = {
    "personal_basic":      "background:#F3F4F6;color:#374151",
    "personal_plus":       "background:#DBEAFE;color:#1E40AF",
    "personal_protect":    "background:#EDE9FE;color:#5B21B6",
    "enterprise_standard": "background:#D1FAE5;color:#065F46",
    "enterprise_plus":     "background:#FEF3C7;color:#92400E",
}


def plan_badge(obj: Account) -> str:
    plan = get_plan(obj.plan)
    style = _PLAN_STYLES.get(obj.plan, "background:#F3F4F6;color:#374151")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style,
        plan.name,
    )
plan_badge.short_description = "Plan"  # type: ignore[attr-defined]
plan_badge.admin_order_field = "plan"  # type: ignore[attr-defined]


# ── Bulk set-plan actions ─────────────────────────────────────────────────────

def _make_set_plan_action(plan_id: str, plan_name: str):
    def action(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(plan=plan_id)
        modeladmin.message_user(request, f"{updated} account(s) moved to {plan_name}.", messages.SUCCESS)
    action.__name__ = f"set_plan_{plan_id}"
    action.short_description = f"Set plan → {plan_name}"  # type: ignore[attr-defined]
    return action


SET_PLAN_ACTIONS = [_make_set_plan_action(p.id, p.name) for p in PLANS]


# ── Bulk actions ─────────────────────────────────────────────────────────────

@admin.action(description="Deactivate selected users")
def action_deactivate(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> None:
    updated = queryset.filter(is_active=True).update(is_active=False)
    modeladmin.message_user(request, f"{updated} user(s) deactivated.", messages.WARNING)


@admin.action(description="Reactivate selected users")
def action_reactivate(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> None:
    updated = queryset.filter(is_active=False).update(is_active=True)
    modeladmin.message_user(request, f"{updated} user(s) reactivated.", messages.SUCCESS)


# ── Status badge ─────────────────────────────────────────────────────────────

def active_badge(obj: User) -> str:
    if obj.is_active:
        return format_html(
            '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;background:#D1FAE5;color:#065F46;">Active</span>'
        )
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;background:#FEE2E2;color:#991B1B;">Inactive</span>'
    )
active_badge.short_description = "Status"  # type: ignore[attr-defined]


# ── Inline ────────────────────────────────────────────────────────────────────

class AccountInline(admin.StackedInline):
    model = Account
    extra = 0
    fields = ("full_name", "email", "phone", "created_at")
    readonly_fields = ("created_at",)
    can_delete = False
    verbose_name_plural = "Account profile"


# ── User admin ────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "phone", active_badge, "is_staff", "agreement_count", "created_at")
    search_fields = ("phone", "account__email", "account__full_name")
    ordering = ("-created_at",)
    actions = [action_deactivate, action_reactivate]
    inlines = [AccountInline]

    fieldsets = (
        (None, {"fields": ("phone",)}),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at")

    add_fieldsets = (
        (None, {"fields": ("phone",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(agreement_count=Count("account__created_agreements", distinct=True))
        )

    def agreement_count(self, obj: User) -> int:
        return obj.agreement_count  # type: ignore[attr-defined]
    agreement_count.short_description = "Agreements"  # type: ignore[attr-defined]
    agreement_count.admin_order_field = "agreement_count"  # type: ignore[attr-defined]


# ── Account admin ─────────────────────────────────────────────────────────────

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "phone", plan_badge, "user_link", "agreement_count", "created_at")
    list_filter = ("plan",)
    search_fields = ("email", "full_name", "phone", "user__phone")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("user_link", "created_at", "updated_at", "agreement_count")
    actions = SET_PLAN_ACTIONS

    fieldsets = (
        ("Identity", {
            "fields": ("full_name", "email", "phone", "user_link"),
        }),
        ("Plan", {
            "fields": ("plan",),
        }),
        ("Stats", {
            "fields": ("agreement_count", "created_at", "updated_at"),
        }),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .annotate(agreement_count=Count("created_agreements", distinct=True))
        )

    def user_link(self, obj: Account) -> str:
        url = f"/admin/accounts/user/{obj.user_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.user.phone)
    user_link.short_description = "User"  # type: ignore[attr-defined]

    def agreement_count(self, obj: Account) -> int:
        return obj.agreement_count  # type: ignore[attr-defined]
    agreement_count.short_description = "Agreements"  # type: ignore[attr-defined]
    agreement_count.admin_order_field = "agreement_count"  # type: ignore[attr-defined]


# ── DeviceSession admin ───────────────────────────────────────────────────────

_SESSION_STATUS_STYLES = {
    True:  "background:#FEE2E2;color:#991B1B",   # revoked
    False: "background:#D1FAE5;color:#065F46",   # active
}


def session_status_badge(obj: DeviceSession) -> str:
    label = "Revoked" if obj.is_revoked else "Active"
    style = _SESSION_STATUS_STYLES[obj.is_revoked]
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style, label,
    )
session_status_badge.short_description = "Status"  # type: ignore[attr-defined]


@admin.action(description="Revoke selected sessions")
def action_revoke_sessions(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    from django.utils import timezone
    updated = queryset.filter(is_revoked=False).update(
        is_revoked=True,
        revoked_at=timezone.now(),
        revoked_reason="admin",
    )
    modeladmin.message_user(request, f"{updated} session(s) revoked.", messages.WARNING)


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user_phone", "client_type", session_status_badge, "device_name", "last_used_at", "expires_at")
    list_filter = ("client_type", "is_revoked")
    search_fields = ("user__phone", "device_name", "device_fingerprint")
    ordering = ("-last_used_at",)
    date_hierarchy = "created_at"
    actions = [action_revoke_sessions]
    readonly_fields = ("id", "user", "client_type", "device_name", "device_fingerprint",
                       "created_at", "last_used_at", "expires_at", "revoked_at", "revoked_reason")

    def user_phone(self, obj: DeviceSession) -> str:
        url = f"/admin/accounts/user/{obj.user_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.user.phone)
    user_phone.short_description = "User"  # type: ignore[attr-defined]
