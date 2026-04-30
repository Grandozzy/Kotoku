"""Structured logging utilities for Kotoku.

Provides a JSON log formatter and a thread-local request-ID store that
middleware populates so every log line in a request context carries a
correlation ID.
"""
from __future__ import annotations

import json
import logging
import threading

_local = threading.local()


def get_request_id() -> str:
    """Return the current request's correlation ID, or an empty string."""
    return getattr(_local, "request_id", "")


def set_request_id(value: str) -> None:
    _local.request_id = value


def clear_request_id() -> None:
    _local.request_id = ""


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Fields: timestamp, level, logger, module, message, request_id (if set),
    plus any extra kwargs passed to the logger call.
    """

    _SKIP = frozenset({
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs",
        "message", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName",
        "exc_info", "exc_text", "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id

        for key, value in record.__dict__.items():
            if key not in self._SKIP and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# Convenience module-level logger for code that imports common.logging directly.
logger = logging.getLogger("kotoku")
