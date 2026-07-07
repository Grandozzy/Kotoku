from django import forms
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.disputes.models import Dispute
from apps.disputes.services import DisputeService
from common.exceptions import DomainError

# ── Inline resolution form ──────────────────────────────────────────────────

class ResolutionForm(forms.Form):
    resolution_note = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 4,
            "style": "width:100%;",
            "placeholder": "Write a clear resolution or dismissal note…",
        }),
        label="Resolution / dismissal note",
        required=True,
    )


# ── Status badge ────────────────────────────────────────────────────────────

_STATUS_STYLES = {
    "open":          "background:#FEF3C7;color:#92400E",
    "investigating": "background:#DBEAFE;color:#1E40AF",
    "resolved":      "background:#D1FAE5;color:#065F46",
    "dismissed":     "background:#F3F4F6;color:#6B7280",
}

def coloured_status(obj: Dispute) -> str:
    style = _STATUS_STYLES.get(obj.status, "")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style,
        obj.get_status_display(),
    )
coloured_status.short_description = "Status"  # type: ignore[attr-defined]


# ── Bulk action ─────────────────────────────────────────────────────────────

@admin.action(description="Mark selected disputes as Investigating")
def action_mark_investigating(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    updated = 0
    for dispute in queryset.filter(status=Dispute.Status.OPEN):
        try:
            DisputeService.mark_investigating(dispute=dispute, actor=str(request.user))
            updated += 1
        except DomainError:
            pass
    modeladmin.message_user(request, f"{updated} dispute(s) marked as Investigating.", messages.SUCCESS)


# ── Admin class ─────────────────────────────────────────────────────────────

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):

    # ── List view ───────────────────────────────────────────────────────────
    list_display = ("id", "agreement_link", "raised_by", coloured_status, "created_at", "resolved_at")
    list_filter = ("status", "created_at")
    search_fields = ("reason", "resolution", "agreement__title", "raised_by__display_name")
    list_select_related = ("agreement", "raised_by")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = [action_mark_investigating]

    # ── Detail view ─────────────────────────────────────────────────────────
    readonly_fields = (
        "agreement_link",
        "raised_by",
        coloured_status,
        "reason",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Dispute", {
            "fields": ("agreement_link", "raised_by", coloured_status, "created_at"),
        }),
        ("Reason submitted by party", {
            "fields": ("reason",),
        }),
        ("Resolution", {
            "fields": ("status", "resolution", "resolved_at", "updated_at"),
        }),
    )

    def agreement_link(self, obj: Dispute):
        url = f"/admin/agreements/agreement/{obj.agreement_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.agreement.title)
    agreement_link.short_description = "Agreement"  # type: ignore[attr-defined]

    # ── Custom change view — inject resolve / dismiss form ──────────────────

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context=None,
    ):
        extra_context = extra_context or {}
        dispute = self.get_object(request, object_id)

        if request.method == "POST":
            action = request.POST.get("_dispute_action")
            if action in ("resolve", "dismiss"):
                form = ResolutionForm(request.POST)
                if form.is_valid():
                    note = form.cleaned_data["resolution_note"]
                    try:
                        if action == "resolve":
                            DisputeService.resolve_dispute(
                                dispute=dispute, resolution=note, actor=str(request.user)
                            )
                            self.message_user(request, "Dispute marked as resolved.", messages.SUCCESS)
                        else:
                            DisputeService.dismiss_dispute(
                                dispute=dispute, resolution=note, actor=str(request.user)
                            )
                            self.message_user(request, "Dispute dismissed.", messages.WARNING)
                        # Reload so fieldsets reflect the new status
                        return self.response_change(request, dispute)
                    except DomainError as exc:
                        self.message_user(request, str(exc), messages.ERROR)
                        extra_context["resolution_form"] = form
                else:
                    extra_context["resolution_form"] = form

        if "resolution_form" not in extra_context:
            extra_context["resolution_form"] = ResolutionForm()

        extra_context["dispute"] = dispute
        extra_context["can_act"] = dispute and dispute.status in (
            Dispute.Status.OPEN,
            Dispute.Status.INVESTIGATING,
        )
        return super().change_view(request, object_id, form_url, extra_context)
