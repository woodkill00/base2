from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service: str):
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        # Common structured fields (only included when present).
        for key in (
            "path",
            "method",
            "status",
            "latency_ms",
            "client_ip",
            "user_agent",
            "task_id",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            # Never break the app due to logging serialization.
            return json.dumps(
                {
                    "timestamp": timestamp,
                    "level": record.levelname,
                    "service": self._service,
                    "logger": record.name,
                    "message": "log_serialize_failed",
                }
            )


def configure_logging(*, service: str) -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service=service))

    root = logging.getLogger()
    root.setLevel(level)

    # Replace existing handlers to prevent duplicated logs in container runtimes.
    root.handlers = [handler]

    # Keep common noisy libraries from spamming JSON logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
