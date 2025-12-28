import os
import sys

# Ensure repo root is importable for tests run in containers.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.tasks import app


def test_celery_accepts_json_only():
    accept_content = list(app.conf.get("accept_content") or [])
    assert "json" in accept_content
    assert "pickle" not in [v.lower() for v in accept_content]

    assert (app.conf.get("task_serializer") or "").lower() == "json"
    assert (app.conf.get("result_serializer") or "").lower() == "json"
