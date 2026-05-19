import pytest

from apps.audit.selectors import AuditSelector
from apps.audit.services import AuditService


def _log(entity_type, entity_id, event_type="test.event"):
    AuditService.record_event(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
    )


@pytest.mark.django_db
class TestAuditSelectorListForEntity:
    def test_returns_matching_logs(self):
        _log("user", "1")
        _log("user", "1")
        result = AuditSelector.list_for_entity("user", "1")
        assert result.count() == 2

    def test_filters_by_entity_type(self):
        _log("user", "1")
        _log("account", "1")
        result = AuditSelector.list_for_entity("user", "1")
        assert result.count() == 1

    def test_filters_by_entity_id(self):
        _log("user", "1")
        _log("user", "2")
        result = AuditSelector.list_for_entity("user", "2")
        assert result.count() == 1
        assert result.first().entity_id == "2"

    def test_returns_empty_when_no_match(self):
        result = AuditSelector.list_for_entity("user", "nonexistent")
        assert result.count() == 0


@pytest.mark.django_db
class TestAuditSelectorListRecent:
    def test_returns_all_within_limit(self):
        for i in range(5):
            _log("user", str(i))
        result = list(AuditSelector.list_recent(limit=10))
        assert len(result) == 5

    def test_respects_limit(self):
        for i in range(10):
            _log("user", str(i))
        result = list(AuditSelector.list_recent(limit=3))
        assert len(result) == 3

    def test_default_limit_is_50(self):
        for i in range(60):
            _log("user", str(i))
        result = list(AuditSelector.list_recent())
        assert len(result) == 50
