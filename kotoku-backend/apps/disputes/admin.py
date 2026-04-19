from django.contrib import admin

from .models import Dispute


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("id", "agreement", "raised_by", "status", "created_at")
    list_select_related = ("agreement", "raised_by")
    search_fields = ("reason",)
    list_filter = ("status",)
