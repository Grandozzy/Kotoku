from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.vault.services import VaultService
from common.exceptions import DomainError
from infrastructure.storage.s3 import S3StorageClient

from .models import VaultEntry


# ── PDF status badge ─────────────────────────────────────────────────────────

_PDF_STATUS_STYLES = {
    "pending":    "background:#F3F4F6;color:#374151",
    "generating": "background:#DBEAFE;color:#1E40AF",
    "ready":      "background:#D1FAE5;color:#065F46",
    "failed":     "background:#FEE2E2;color:#991B1B",
}


def coloured_pdf_status(obj: VaultEntry) -> str:
    style = _PDF_STATUS_STYLES.get(obj.pdf_status, "")
    return format_html(
        '<span style="padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;{}">{}</span>',
        style,
        obj.get_pdf_status_display(),
    )
coloured_pdf_status.short_description = "PDF status"  # type: ignore[attr-defined]


def archived_badge(obj: VaultEntry) -> str:
    if obj.archived:
        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;background:#F9FAFB;color:#9CA3AF;">Archived</span>'
        )
    return "—"
archived_badge.short_description = "Archived"  # type: ignore[attr-defined]


# ── Bulk action ──────────────────────────────────────────────────────────────

@admin.action(description="Retry PDF generation for selected entries")
def action_retry_pdf(
    modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
) -> None:
    retried = 0
    for entry in queryset.filter(pdf_status=VaultEntry.PdfStatus.FAILED):
        try:
            VaultService.retry_export(agreement_id=entry.agreement_id)
            retried += 1
        except DomainError:
            pass
    modeladmin.message_user(request, f"PDF generation queued for {retried} entry/entries.", messages.SUCCESS)


# ── Admin class ──────────────────────────────────────────────────────────────

@admin.register(VaultEntry)
class VaultEntryAdmin(admin.ModelAdmin):

    # ── List view ────────────────────────────────────────────────────────────
    list_display = ("id", "agreement_link", coloured_pdf_status, archived_badge, "retain_until", "created_at")
    list_select_related = ("agreement",)
    list_filter = ("pdf_status", "archived", "created_at")
    search_fields = ("agreement__title", "agreement__seal_hash")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = [action_retry_pdf]

    # ── Detail view ──────────────────────────────────────────────────────────
    readonly_fields = (
        "agreement_link",
        "seal_hash_display",
        coloured_pdf_status,
        "pdf_key",
        "pdf_download_link",
        "retain_until",
        "archived",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Agreement", {
            "fields": ("agreement_link", "seal_hash_display"),
        }),
        ("PDF export", {
            "fields": (coloured_pdf_status, "pdf_key", "pdf_download_link"),
        }),
        ("Retention", {
            "fields": ("retain_until", "archived", "created_at", "updated_at"),
        }),
    )

    def agreement_link(self, obj: VaultEntry) -> str:
        url = f"/admin/agreements/agreement/{obj.agreement_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.agreement.title)
    agreement_link.short_description = "Agreement"  # type: ignore[attr-defined]

    def seal_hash_display(self, obj: VaultEntry) -> str:
        h = obj.agreement.seal_hash if obj.agreement_id else ""
        if h:
            return format_html('<code style="font-size:12px;">{}</code>', h)
        return "—"
    seal_hash_display.short_description = "Seal hash"  # type: ignore[attr-defined]

    def pdf_download_link(self, obj: VaultEntry) -> str:
        if obj.pdf_status != VaultEntry.PdfStatus.READY or not obj.pdf_key:
            return "—"
        try:
            url = S3StorageClient().generate_presigned_url(obj.pdf_key, expires_in=3600)
            return format_html('<a href="{}" target="_blank">Download PDF (1 hr link)</a>', url)
        except Exception:
            return "Could not generate link"
    pdf_download_link.short_description = "Download"  # type: ignore[attr-defined]
