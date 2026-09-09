from __future__ import annotations

import os

from fastapi import FastAPI

from api.routes.test_support import router


if os.getenv("E2E_TEST_MODE", "").strip().lower() != "true":
    raise RuntimeError("test_support_mode_required")
if not os.getenv("E2E_TEST_KEY", "").strip():
    raise RuntimeError("test_support_key_required")

app = FastAPI(
    title="Base2 synthetic test support",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router, prefix="/api")


@app.get("/synthetic-health", include_in_schema=False)
def health() -> dict[str, bool]:
    """Expose only process readiness for the loopback-only synthetic service."""

    return {"ok": True}
