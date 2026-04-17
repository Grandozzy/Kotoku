from apps.audit.models import AuditLog


class AuditSelector:
    @staticmethod
    def list_for_entity(entity_type: str, entity_id: str):
        return AuditLog.objects.filter(entity_type=entity_type, entity_id=entity_id)

    @staticmethod
    def list_recent(limit: int = 50):
        return AuditLog.objects.all()[:limit]
