from django.contrib import admin

from .models import VaultEntry


@admin.register(VaultEntry)
class VaultEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "agreement", "evidence_item", "sealed_at", "archived")
    list_select_related = ("agreement", "evidence_item")
    list_filter = ("archived",)
