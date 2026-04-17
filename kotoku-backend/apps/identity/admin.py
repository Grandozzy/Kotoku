from django.contrib import admin

from .models import IdentityRecord


@admin.register(IdentityRecord)
class IdentityRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "reference", "verification_type", "verified_at")
