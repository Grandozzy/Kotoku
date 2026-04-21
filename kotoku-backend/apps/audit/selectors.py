from typing import TYPE_CHECKING

from apps.audit.models import AuditLog

if TYPE_CHECKING:
    from django.db.models import QuerySet


class AuditSelector:
    @staticmethod
    def list_for_entity(entity_type: str, entity_id: str) -> "QuerySet[AuditLog]":
        return AuditLog.objects.filter(entity_type=entity_type, entity_id=entity_id)

    @staticmethod
    def list_recent(limit: int = 50) -> "QuerySet[AuditLog]":
        return AuditLog.objects.all()[:limit]
