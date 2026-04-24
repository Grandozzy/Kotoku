from django.contrib import admin

from apps.templates.models import ScenarioTemplate


@admin.register(ScenarioTemplate)
class ScenarioTemplateAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "version", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("slug", "name")
    readonly_fields = ("created_at", "updated_at")
