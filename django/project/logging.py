from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from project.middleware.request_id import get_request_id


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
            return json.dumps(
                {
                    "timestamp": timestamp,
                    "level": record.levelname,
                    "service": self._service,
                    "logger": record.name,
                    "message": "log_serialize_failed",
                }
            )
