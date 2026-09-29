from django.contrib import admin, messages
from django.utils.html import format_html

from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord, PartyIdentityVerification
from apps.identity.services import IdentityService
from common.exceptions import DomainError
from infrastructure.storage.s3 import S3StorageClient


@admin.register(IdentityRecord)
class IdentityRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "reference", "verification_type", "verified_at")
    list_select_related = ("account",)
    search_fields = ("reference", "account__email")
    list_filter = ("verification_type",)


@admin.register(PartyIdentityVerification)
class PartyIdentityVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "party",
        "status",
        "ocr_pin",
        "face_match_score",
        "verified_at",
        "updated_at",
    )
    list_select_related = ("party", "party__agreement")
    search_fields = ("party__display_name", "party__id_number", "ocr_pin", "ocr_full_name")
    list_filter = ("status",)
    readonly_fields = (
        "failure_codes",
        "detail",
        "liveness_confidence",
        "liveness_reference_s3_key",
        "liveness_reference_delete_after",
        "front_card_preview",
        "back_card_preview",
        "liveness_preview",
        "face_match_score",
        "verified_at",
    )
    actions = ("approve_manual_review", "reject_manual_review")

    def _evidence_preview(self, evidence_id: int | None):
        if not evidence_id:
            return "Not available"
        item = EvidenceItem.objects.filter(pk=evidence_id).only("file_key", "mime_type").first()
        if not item:
            return "Not available"
        url = S3StorageClient().generate_presigned_view_url(
            item.file_key,
            content_type=item.mime_type,
        )
        return format_html('<a href="{}" target="_blank" rel="noopener">Open image</a>', url)

    @admin.display(description="Ghana Card front")
    def front_card_preview(self, obj):
        return self._evidence_preview(obj.front_evidence_id)

    @admin.display(description="Ghana Card back")
    def back_card_preview(self, obj):
        return self._evidence_preview(obj.back_evidence_id)

    @admin.display(description="Liveness reference")
    def liveness_preview(self, obj):
        if not obj.liveness_reference_s3_key:
            return "Not available"
        url = S3StorageClient().generate_presigned_view_url(
            obj.liveness_reference_s3_key,
            content_type="image/jpeg",
        )
        return format_html('<a href="{}" target="_blank" rel="noopener">Open image</a>', url)

    @admin.action(description="Approve eligible manual reviews")
    def approve_manual_review(self, request, queryset):
        self._resolve_reviews(request, queryset, approved=True)

    @admin.action(description="Reject eligible manual reviews")
    def reject_manual_review(self, request, queryset):
        self._resolve_reviews(request, queryset, approved=False)

    def _resolve_reviews(self, request, queryset, *, approved: bool) -> None:
        resolved = 0
        skipped = 0
        for verification_id in queryset.values_list("pk", flat=True):
            try:
                IdentityService.resolve_manual_review(
                    verification_id=verification_id,
                    approved=approved,
                    actor=f"admin:{request.user.pk}",
                )
                resolved += 1
            except DomainError:
                skipped += 1
        if resolved:
            self.message_user(request, f"Resolved {resolved} identity review(s).")
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} ineligible review(s).",
                level=messages.WARNING,
            )
