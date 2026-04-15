from django.db import models


class AuditLog(models.Model):
    event_type = models.CharField(max_length=128)
    actor = models.CharField(max_length=128, blank=True)
    entity_type = models.CharField(max_length=128)
    entity_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
