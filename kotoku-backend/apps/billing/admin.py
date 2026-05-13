from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.accounts.models import Account
from apps.billing.constants import PLANS, get_plan
from apps.billing.selectors import _check_business_misuse


# ── Plan badge ────────────────────────────────────────────────────────────────

_PLAN_STYLES = {
    "personal_basic":    "background:#F3F4F6;color:#374151",
    "personal_plus":     "background:#DBEAFE;color:#1E40AF",
    "personal_protect":  "background:#EDE9FE;color:#5B21B6",
    "enterprise_standard": "background:#D1FAE5;color:#065F46",
    "enterprise_plus":   "background:#FEF3C7;color:#92400E",
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


def misuse_flag(obj: Account) -> str:
    plan = get_plan(obj.plan)
    suspected = _check_business_misuse(obj, plan)
    if suspected:
        return format_html(
            '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;'
            'background:#FEF3C7;color:#92400E;">⚑ Review</span>'
        )
    return "—"
misuse_flag.short_description = "Misuse"  # type: ignore[attr-defined]


# ── Bulk set-plan actions ─────────────────────────────────────────────────────

def _make_set_plan_action(plan_id: str, plan_name: str):
    def action(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(plan=plan_id)
        modeladmin.message_user(
            request,
            f"{updated} account(s) moved to {plan_name}.",
            messages.SUCCESS,
        )
    action.__name__ = f"set_plan_{plan_id}"
    action.short_description = f"Set plan → {plan_name}"  # type: ignore[attr-defined]
    return action


SET_PLAN_ACTIONS = [
    _make_set_plan_action(p.id, p.name)
    for p in PLANS
]


# ── Billing admin for Account ─────────────────────────────────────────────────

class BillingAccountAdmin(admin.ModelAdmin):
    """
    A focused view of Account through the billing lens.
    Registered under the billing app label so it appears in its own section.
    """

    # Re-use Account model as a proxy through billing app
    list_display = ("id", "full_name_link", "phone", plan_badge, misuse_flag, "created_at")
    list_filter = ("plan",)
    search_fields = ("email", "full_name", "phone", "user__phone")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = SET_PLAN_ACTIONS
    readonly_fields = ("full_name_link", "email", "phone", "created_at")

    fieldsets = (
        ("Account", {
            "fields": ("full_name_link", "email", "phone", "created_at"),
        }),
        ("Plan", {
            "fields": ("plan",),
        }),
    )

    def full_name_link(self, obj: Account) -> str:
        url = f"/admin/accounts/account/{obj.pk}/change/"
        label = obj.full_name or obj.email
        return format_html('<a href="{}">{}</a>', url, label)
    full_name_link.short_description = "Account"  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


# ── AccountProxy ──────────────────────────────────────────────────────────────
# Register a proxy model under the billing app so the billing admin section
# has its own "Plan management" entry without conflicting with AccountAdmin.

class AccountPlanProxy(Account):
    class Meta:
        proxy = True
        app_label = "billing"
        verbose_name = "Account plan"
        verbose_name_plural = "Account plans"


admin.site.register(AccountPlanProxy, BillingAccountAdmin)
