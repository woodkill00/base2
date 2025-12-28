from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("django.request")

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started = time.perf_counter()
        req_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        token = _request_id_ctx.set(req_id)
        request.request_id = req_id
        try:
            response = self.get_response(request)
        except Exception:
            logger.exception(
                "django_request_error",
                extra={
                    "method": request.method,
                    "path": request.path,
                },
            )
            raise
        else:
            try:
                response["X-Request-Id"] = req_id
            except Exception:
                pass

            latency_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "django_request",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status": getattr(response, "status_code", None),
                    "latency_ms": round(latency_ms, 3),
                },
            )
            return response
        finally:
            try:
                _request_id_ctx.reset(token)
            except Exception:
                pass
