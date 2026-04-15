from apps.audit.models import AuditLog


class AuditService:
    """Append-only audit logging for important write paths."""

    @staticmethod
    def record_event(
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str = "",
        metadata: dict | None = None,
    ) -> AuditLog:
        return AuditLog.objects.create(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata or {},
        )
