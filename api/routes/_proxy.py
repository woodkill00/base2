from __future__ import annotations

from typing import Any, Mapping

from fastapi import HTTPException, Request, Response

from api.clients.django_client import django_request


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _apply_set_cookie_headers(response: Response, headers: Mapping[str, Any]) -> None:
    # httpx may provide get_list('set-cookie') style data; our client returns
    # either a string or list under the 'set-cookie' key.
    set_cookie = headers.get("set-cookie")
    if isinstance(set_cookie, list):
        for v in set_cookie:
            response.headers.append("set-cookie", v)
    elif isinstance(set_cookie, str) and set_cookie:
        response.headers.append("set-cookie", set_cookie)


async def proxy_json(
    *,
    request: Request,
    response: Response,
    method: str,
    upstream_path: str,
    json_body: Any | None,
    forward_csrf: bool = True,
) -> Any:
    forward_headers: dict[str, str] = {}
    if forward_csrf:
        csrf = request.headers.get("x-csrf-token")
        if csrf:
            forward_headers["X-CSRF-Token"] = csrf

    status, data, headers = await django_request(
        method=method,
        path=upstream_path,
        json_body=json_body,
        cookies=request.cookies,
        headers=forward_headers,
    )

    _apply_set_cookie_headers(response, headers)

    if status == 204:
        response.status_code = 204
        return None

    response.status_code = status
    if data is None:
        return None

    # Ensure error shape stays compatible.
    if isinstance(data, dict) and "detail" in data:
        return data

    return data


def require_session_cookie(request: Request, cookie_name: str) -> None:
    if not request.cookies.get(cookie_name):
        raise HTTPException(status_code=401, detail="Not authenticated")
