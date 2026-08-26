#!/usr/bin/env python3
"""Credential-safe outside-in verification for the guarded full preview."""

from __future__ import annotations

from dataclasses import dataclass
import base64
import http.client
import ipaddress
import json
import re
import ssl
from typing import Callable

from digital_ocean.scripts.python.full_preview_policy import full_preview_policy


SAFE_DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


def _request(host: str, path: str, ip_address: str, authorization: str | None) -> Response:
    context = ssl._create_unverified_context()
    connection = http.client.HTTPSConnection(ip_address, 443, timeout=15, context=context)
    headers = {"Host": host, "User-Agent": "base2-full-preview-probe/1"}
    if authorization:
        headers["Authorization"] = authorization
    try:
        connection.request("GET", path, headers=headers)
        reply = connection.getresponse()
        body = reply.read(262_145)
        if len(body) > 262_144:
            raise ProbeError("probe response exceeded safe bound")
        return Response(reply.status, {k.lower(): v for k, v in reply.getheaders()}, body)
    finally:
        connection.close()


def verify_full_preview(
    domain: str,
    ip_address: str,
    *,
    username: str,
    password: str,
    owner_cidrs: list[str],
    transport: Callable[[str, str, str, str | None], Response] = _request,
) -> dict:
    if not SAFE_DOMAIN.fullmatch(domain):
        raise ProbeError("probe domain is invalid")
    try:
        address = str(ipaddress.ip_address(ip_address))
    except ValueError as exc:
        raise ProbeError("probe IP is invalid") from exc
    if not username or not password or any(value in username + password for value in ("\n", "\r", ":")):
        raise ProbeError("probe credentials are invalid")
    policy = full_preview_policy(domain, owner_cidrs)
    authorization = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
    results = []
    for route in policy["routes"]:
        public = route["exposure"] == "public"
        anonymous = transport(route["host"], route["path"], address, None)
        if public:
            if not 200 <= anonymous.status < 400:
                raise ProbeError(f"public route failed: {route['service']}")
            authorized_status = None
        else:
            if anonymous.status not in {401, 403}:
                raise ProbeError(f"protected route was anonymously reachable: {route['service']}")
            authorized = transport(route["host"], route["path"], address, authorization)
            if not 200 <= authorized.status < 400:
                raise ProbeError(f"authorized route failed: {route['service']}")
            authorized_status = authorized.status
        results.append({
            "service": route["service"], "exposure": route["exposure"],
            "anonymousStatus": anonymous.status, "authorizedStatus": authorized_status,
        })
    return {
        "schemaVersion": 1, "ok": True, "mode": "full-preview",
        "routeCount": len(results), "results": results,
        "credentialsReturned": False, "responseBodiesReturned": False,
    }


def safe_json(receipt: dict) -> str:
    return json.dumps(receipt, sort_keys=True, separators=(",", ":"))
