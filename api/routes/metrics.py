from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from api.metrics import metrics

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    # Prometheus text exposition format (v0.0.4).
    return Response(content=metrics.render_prometheus(), media_type="text/plain; version=0.0.4")
