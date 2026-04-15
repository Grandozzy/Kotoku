from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "entity_type", "entity_id", "actor", "created_at")
    list_filter = ("event_type", "entity_type", "created_at")
    readonly_fields = ("event_type", "entity_type", "entity_id", "actor", "metadata", "created_at")
