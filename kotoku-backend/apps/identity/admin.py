from django.contrib import admin

from .models import IdentityRecord, PartyIdentityVerification


@admin.register(IdentityRecord)
class IdentityRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "reference", "verification_type", "verified_at")
    list_select_related = ("account",)
    search_fields = ("reference", "account__email")
    list_filter = ("verification_type",)


@admin.register(PartyIdentityVerification)
class PartyIdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "status", "ocr_pin", "face_match_score", "verified_at", "updated_at")
    list_select_related = ("party", "party__agreement")
    search_fields = ("party__display_name", "party__id_number", "ocr_pin", "ocr_full_name")
    list_filter = ("status",)
