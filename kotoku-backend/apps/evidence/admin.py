from django.contrib import admin

from .models import EvidenceItem


@admin.register(EvidenceItem)
class EvidenceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "agreement", "file_type", "original_name", "created_at")
