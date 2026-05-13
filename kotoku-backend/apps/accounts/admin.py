from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from .models import Account, User


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
    list_display = ("id", "full_name", "email", "phone", "plan", "user_link", "agreement_count", "created_at")
    list_filter = ("plan",)
    search_fields = ("email", "full_name", "phone", "user__phone")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("user_link", "created_at", "updated_at", "agreement_count")

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
