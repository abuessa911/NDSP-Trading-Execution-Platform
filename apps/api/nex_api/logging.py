import logging
import json
from collections.abc import MutableMapping
from typing import Any
from uuid import UUID

import structlog


def redact_event(_: Any, __: str, event: MutableMapping[str, Any]) -> dict[str, Any]:
    # Only server-generated identifiers/constant events are permitted. Free-form
    # messages, exceptions and library arguments can contain connection secrets.
    allowed_events = {"unhandled_request_error", "audit_persistence_unavailable"}
    try:
        correlation = str(UUID(str(event.get("correlation_id"))))
    except ValueError:
        correlation = None
    return {
        "event": event.get("event") if event.get("event") in allowed_events else "redacted",
        "correlation_id": correlation,
        "level": event.get("level"),
    }


class LibraryRedaction(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            payload = json.loads(record.getMessage()) if record.name.startswith("nex.") else None
            if not isinstance(payload, dict):
                raise ValueError()
            record.msg = json.dumps(redact_event(None, "", payload))
            record.args = ()
        except (ValueError, TypeError):
            record.msg = "[library log redacted]"
            record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for handler in logging.getLogger().handlers:
        handler.addFilter(LibraryRedaction())
    for item in logging.Logger.manager.loggerDict.values():
        if isinstance(item, logging.Logger):
            for handler in item.handlers:
                handler.addFilter(LibraryRedaction())
    structlog.configure(
        processors=[structlog.processors.add_log_level, redact_event,
                    structlog.processors.JSONRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )