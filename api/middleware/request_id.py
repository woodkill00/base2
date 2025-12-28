import uuid
from typing import Callable
from fastapi import Request, Response

try:
    from api.logging import set_request_id
except Exception:  # pragma: no cover
    set_request_id = None


async def request_id_middleware(request: Request, call_next: Callable):
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = req_id
    if set_request_id is not None:
        set_request_id(req_id)
    response: Response = await call_next(request)
    response.headers["X-Request-Id"] = req_id
    return response
