from django.contrib import admin

from .models import VaultEntry


@admin.register(VaultEntry)
class VaultEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "agreement",
        "export_status",
        "sealed_at",
        "retention_until",
        "is_free_retention",
        "retry_count",
        "archived",
    )
    list_filter = ("export_status", "archived")
    list_select_related = ("agreement",)
