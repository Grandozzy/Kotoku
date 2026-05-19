import logging
import pytest

from common import constants
from common.logging import JsonFormatter, get_request_id, set_request_id, clear_request_id
from common.mixins import TimestampedServiceMixin
from common.permissions import IsSystemHealthy
from common.types import HealthPayload
from common.validators import ensure_present
from apps.notifications.providers.stub_provider import StubNotificationProvider


def test_service_name_constant():
    assert constants.SERVICE_NAME == "kotoku-backend"


def test_timestamped_service_mixin_instantiable():
    mixin = TimestampedServiceMixin()
    assert mixin is not None


def test_is_system_healthy_always_returns_true():
    perm = IsSystemHealthy()
    assert perm.has_permission(request=None, view=None) is True


def test_health_payload_type():
    payload: HealthPayload = {"status": "ok"}
    assert payload["status"] == "ok"


def test_ensure_present_raises_on_empty():
    with pytest.raises(ValueError, match="phone is required"):
        ensure_present("", "phone")


def test_ensure_present_passes_on_value():
    ensure_present("+233500000001", "phone")  # should not raise


class TestStubNotificationProvider:
    def test_send_returns_true(self):
        provider = StubNotificationProvider()
        result = provider.send(to="+233500000001", body="Hello")
        assert result is True

    def test_send_records_message(self):
        provider = StubNotificationProvider()
        provider.send(to="+233500000001", body="Test")
        assert provider.sent == [("+233500000001", "Test")]

    def test_send_multiple(self):
        provider = StubNotificationProvider()
        provider.send("+1111111111", "A")
        provider.send("+2222222222", "B")
        assert len(provider.sent) == 2


class TestJsonFormatter:
    def _make_record(self, msg="test message", level=logging.INFO):
        record = logging.LogRecord(
            name="kotoku", level=level, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        return record

    def test_formats_as_json(self):
        import json
        formatter = JsonFormatter()
        output = formatter.format(self._make_record())
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert parsed["level"] == "INFO"
        assert "timestamp" in parsed

    def test_includes_request_id_when_set(self):
        import json
        set_request_id("abc-123")
        formatter = JsonFormatter()
        output = formatter.format(self._make_record())
        parsed = json.loads(output)
        assert parsed["request_id"] == "abc-123"
        clear_request_id()

    def test_omits_request_id_when_not_set(self):
        import json
        clear_request_id()
        formatter = JsonFormatter()
        output = formatter.format(self._make_record())
        parsed = json.loads(output)
        assert "request_id" not in parsed

    def test_get_set_clear_request_id(self):
        clear_request_id()
        assert get_request_id() == ""
        set_request_id("xyz")
        assert get_request_id() == "xyz"
        clear_request_id()
        assert get_request_id() == ""

    def test_includes_extra_kwargs_in_output(self):
        import json
        record = self._make_record()
        record.trace_id = "t-999"
        formatter = JsonFormatter()
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["trace_id"] == "t-999"

    def test_includes_exc_info_when_present(self):
        import json
        import sys
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="kotoku", level=logging.ERROR, pathname="", lineno=0,
            msg="error", args=(), exc_info=exc_info,
        )
        formatter = JsonFormatter()
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exc_info" in parsed
        assert "ValueError" in parsed["exc_info"]
