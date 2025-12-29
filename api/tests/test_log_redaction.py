import json
import logging
import os
import sys
from io import StringIO

# Ensure repo root is importable for tests run in containers.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.logging import JsonFormatter, RedactingFilter


def _capture_log(message: str) -> dict:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="api"))
    handler.addFilter(RedactingFilter())

    logger = logging.getLogger("test.redaction")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.info(message)

    raw = stream.getvalue().strip()
    assert raw, "expected JSON log output"
    return json.loads(raw)


def test_redacts_bearer_tokens_in_message():
    payload = _capture_log("Authorization: Bearer supersecrettoken")
    assert "supersecrettoken" not in payload["message"]
    assert "Bearer [REDACTED]" in payload["message"]


def test_redacts_url_credentials_in_message():
    payload = _capture_log("broker=redis://:mypassword@redis:6379/0")
    assert "mypassword" not in payload["message"]
    assert ":[REDACTED]@redis:6379/0" in payload["message"]
