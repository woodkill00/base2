from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from project.middleware.request_id import get_request_id

_SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "jwt",
    "session",
    "csrf",
)


_BEARER_RE = re.compile(r"(?i)\bbearer\s+[^\s]+")
_BASIC_RE = re.compile(r"(?i)\bbasic\s+[^\s]+")
_URL_CRED_RE = re.compile(
    r"(?i)\b(?P<scheme>redis|postgres|postgresql|amqp)://(?:(?P<user>[^:/@\s]+):)?(?P<pw>[^@\s]+)@"
)


def _is_sensitive_key(key: str) -> bool:
    k = key.lower().replace("_", "-")
    return any(fragment in k for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _redact_text(text: str) -> str:
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _BASIC_RE.sub("Basic [REDACTED]", text)
    text = _URL_CRED_RE.sub(
        lambda m: f"{m.group('scheme')}://{m.group('user') or ''}:[REDACTED]@",
        text,
    )
    return text


def _redact_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, bytes):
        return "[REDACTED]"
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for k, v in value.items():
            if _is_sensitive_key(str(k)):
                redacted[str(k)] = "[REDACTED]"
            else:
                redacted[str(k)] = _redact_value(v)
        return redacted
    if isinstance(value, (list, tuple, set)):
        seq = [_redact_value(v) for v in value]
        return seq if isinstance(value, list) else type(value)(seq)
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = _redact_text(record.msg)

            for key, raw in list(record.__dict__.items()):
                if _is_sensitive_key(str(key)):
                    record.__dict__[key] = "[REDACTED]"
                elif isinstance(raw, (dict, list, tuple, set, str, bytes)):
                    record.__dict__[key] = _redact_value(raw)
        except Exception:
            return True
        return True


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
