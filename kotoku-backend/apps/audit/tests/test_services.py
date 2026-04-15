from apps.audit.models import AuditLog
from apps.audit.services import AuditService


def test_record_event_creates_append_only_audit_log(db) -> None:
    AuditService.record_event(
        event_type="agreement.sealed",
        entity_type="agreement",
        entity_id="42",
        actor="tester",
        metadata={"source": "unit-test"},
    )

    event = AuditLog.objects.get()
    assert event.event_type == "agreement.sealed"
    assert event.entity_type == "agreement"
    assert event.entity_id == "42"
    assert event.actor == "tester"
    assert event.metadata["source"] == "unit-test"
