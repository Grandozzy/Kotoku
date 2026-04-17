from django.contrib import admin

from .models import Agreement


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "scenario_template", "created_by", "created_at")
    list_select_related = ("created_by",)
    search_fields = ("title",)
    list_filter = ("status",)
