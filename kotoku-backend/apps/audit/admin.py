import json

from django.contrib import admin
from django.utils.html import format_html

from .models import AuditLog

# ── Event type badge ─────────────────────────────────────────────────────────

_EVENT_COLOURS = {
    "dispute":     "#EDE9FE;color:#5B21B6",
    "agreement":   "#DBEAFE;color:#1E40AF",
    "vault":       "#D1FAE5;color:#065F46",
    "account":     "#FEF3C7;color:#92400E",
    "auth":        "#FEE2E2;color:#991B1B",
    "consent":     "#E0E7FF;color:#3730A3",
    "notification":"#F0FDF4;color:#166534",
}


def coloured_event(obj: AuditLog) -> str:
    prefix = obj.event_type.split(".")[0] if "." in obj.event_type else obj.event_type
    colours = _EVENT_COLOURS.get(prefix, "#F3F4F6;color:#374151")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;background:{}">{}</span>',
        colours,
        obj.event_type,
    )
coloured_event.short_description = "Event"  # type: ignore[attr-defined]


def metadata_pretty(obj: AuditLog) -> str:
    if not obj.metadata:
        return "—"
    try:
        pretty = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        pretty = str(obj.metadata)
    return format_html(
        '<pre style="margin:0;font-size:12px;white-space:pre-wrap;word-break:break-all;'
        'background:#F9FAFB;padding:8px 12px;border-radius:6px;">{}</pre>',
        pretty,
    )
metadata_pretty.short_description = "Metadata"  # type: ignore[attr-defined]


# ── Admin class ───────────────────────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    # ── List view ─────────────────────────────────────────────────────────────
    list_display = (coloured_event, "entity_type", "entity_id", "actor", "created_at")
    list_filter = ("entity_type", "created_at")
    search_fields = ("event_type", "actor", "entity_id", "entity_type")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    # ── Detail view ───────────────────────────────────────────────────────────
    readonly_fields = (
        coloured_event,
        "entity_type",
        "entity_id",
        "actor",
        metadata_pretty,
        "created_at",
    )
    fieldsets = (
        ("Event", {
            "fields": (coloured_event, "entity_type", "entity_id", "actor", "created_at"),
        }),
        ("Metadata", {
            "fields": (metadata_pretty,),
        }),
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False
