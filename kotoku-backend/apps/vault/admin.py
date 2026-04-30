from django.contrib import admin

from .models import VaultEntry


@admin.register(VaultEntry)
class VaultEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "agreement",
        "pdf_status",
        "retain_until",
        "archived",
        "created_at",
    )
    list_select_related = ("agreement",)
    list_filter = ("pdf_status", "archived")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("agreement__title",)
