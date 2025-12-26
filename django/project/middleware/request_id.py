from __future__ import annotations

import uuid
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        req_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        token = _request_id_ctx.set(req_id)
        request.request_id = req_id
        try:
            response = self.get_response(request)
        finally:
            try:
                _request_id_ctx.reset(token)
            except Exception:
                pass

        try:
            response["X-Request-Id"] = req_id
        except Exception:
            pass
        return response
