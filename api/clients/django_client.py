from __future__ import annotations

from typing import Any, Mapping, Tuple

import httpx

from api.settings import settings


async def django_request(
    *,
    method: str,
    path: str,
    json_body: Any | None,
    cookies: Mapping[str, str] | None,
    headers: Mapping[str, str] | None,
) -> Tuple[int, Any | None, Mapping[str, str]]:
    """Make an internal request to Django.

    This is intentionally a small, testable surface: callers pass method/path,
    and we return (status_code, json_or_none, response_headers).

    Tests monkeypatch this function.
    """

    base_url = settings.DJANGO_INTERNAL_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        r = await client.request(
            method.upper(),
            url,
            json=json_body,
            cookies=dict(cookies or {}),
            headers=dict(headers or {}),
        )

    try:
        data = r.json() if r.content else None
    except Exception:
        data = {"detail": "Upstream returned invalid JSON"}

    headers = dict(r.headers)
    try:
        sc = r.headers.get_list("set-cookie")
    except Exception:
        sc = []
    if sc:
        headers["set-cookie"] = sc

    return r.status_code, data, headers
