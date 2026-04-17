from django.contrib import admin

from .models import IdentityRecord


@admin.register(IdentityRecord)
class IdentityRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "reference", "verification_type", "verified_at")
    list_select_related = ("account",)
    search_fields = ("reference", "account__email")
    list_filter = ("verification_type",)
