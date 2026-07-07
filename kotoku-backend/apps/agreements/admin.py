import json

from django.contrib import admin
from django.utils.html import format_html

from apps.parties.models import Party

from .models import Agreement, AgreementRevision, Annotation

# ── Status badge ────────────────────────────────────────────────────────────

_STATUS_STYLES = {
    "draft":             "background:#F3F4F6;color:#374151",
    "pending_consent":   "background:#FEF3C7;color:#92400E",
    "active":            "background:#DBEAFE;color:#1E40AF",
    "sealed":            "background:#D1FAE5;color:#065F46",
    "reopen_requested":  "background:#FEE2E2;color:#991B1B",
    "closed":            "background:#E0E7FF;color:#3730A3",
    "archived":          "background:#F9FAFB;color:#9CA3AF",
    "expired":           "background:#FEF2F2;color:#B91C1C",
}


def coloured_status(obj: Agreement) -> str:
    style = _STATUS_STYLES.get(obj.status, "")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style,
        obj.get_status_display(),
    )
coloured_status.short_description = "Status"  # type: ignore[attr-defined]


def seal_hash_short(obj: Agreement) -> str:
    if obj.seal_hash:
        return format_html(
            '<code style="font-size:11px;color:#374151;">{}</code>',
            obj.seal_hash[:16] + "…",
        )
    return "—"
seal_hash_short.short_description = "Seal hash"  # type: ignore[attr-defined]


# ── Inlines ─────────────────────────────────────────────────────────────────

class PartyInline(admin.TabularInline):
    model = Party
    extra = 0
    fields = ("display_name", "role", "phone", "id_type", "id_number")
    readonly_fields = ("display_name", "role", "phone", "id_type", "id_number")
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Parties"


class AnnotationInline(admin.TabularInline):
    model = Annotation
    extra = 0
    fields = ("author_party", "body", "created_at")
    readonly_fields = ("author_party", "body", "created_at")
    can_delete = False
    ordering = ("created_at",)


class RevisionInline(admin.TabularInline):
    model = AgreementRevision
    extra = 0
    fields = ("revision_number", "seal_hash", "sealed_at")
    readonly_fields = ("revision_number", "seal_hash", "sealed_at")
    can_delete = False
    ordering = ("-revision_number",)
    verbose_name_plural = "Revisions"


# ── Admin class ─────────────────────────────────────────────────────────────

@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):

    # ── List view ───────────────────────────────────────────────────────────
    list_display = ("id", "title", coloured_status, "scenario_template", "created_by", seal_hash_short, "created_at")
    list_select_related = ("created_by",)
    list_filter = ("status", "scenario_template", "created_at")
    search_fields = ("title", "seal_hash", "created_by__email", "created_by__full_name")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    # ── Detail view ─────────────────────────────────────────────────────────
    readonly_fields = (
        "created_by",
        coloured_status,
        "seal_hash",
        "sealed_at",
        "closed_at",
        "created_at",
        "updated_at",
        "field_data_pretty",
    )
    fieldsets = (
        ("Agreement", {
            "fields": ("title", "description", coloured_status, "scenario_template", "created_by", "created_at"),
        }),
        ("Seal", {
            "fields": ("seal_hash", "sealed_at", "closed_at"),
            "classes": ("collapse",),
        }),
        ("Field data", {
            "fields": ("field_data_pretty",),
            "classes": ("collapse",),
        }),
    )
    inlines = [PartyInline, AnnotationInline, RevisionInline]

    def field_data_pretty(self, obj: Agreement) -> str:
        if not obj.field_data:
            return "—"
        pretty = json.dumps(obj.field_data, indent=2, ensure_ascii=False)
        return format_html(
            '<pre style="margin:0;font-size:12px;white-space:pre-wrap;word-break:break-all;">{}</pre>',
            pretty,
        )
    field_data_pretty.short_description = "Field data (JSON)"  # type: ignore[attr-defined]
