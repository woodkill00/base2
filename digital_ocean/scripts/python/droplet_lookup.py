#!/usr/bin/env python3
"""Resolve one DigitalOcean droplet name without treating uncertainty as absence."""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from digital_ocean.scripts.python.provider_lease import (
        GitRemoteLeaseStore,
        acquire_provider_lease,
        release_provider_lease,
    )
except ModuleNotFoundError:
    from provider_lease import GitRemoteLeaseStore, acquire_provider_lease, release_provider_lease

__all__ = [
    "GitRemoteLeaseStore",
    "acquire_provider_lease",
    "list_named_droplets",
    "lookup",
    "release_provider_lease",
    "resolve_name",
]


def resolve_name(raw_name: str | None, project: str) -> str:
    value = raw_name or f"{project}-droplet"
    resolved = value.replace("${PROJECT_NAME}", project).replace("$PROJECT_NAME", project)
    if "${" in resolved or "$(" in resolved:
        raise ValueError("invalid_droplet_name_template")
    name = resolved.strip()
    if not name:
        raise ValueError("empty_droplet_name")
    return name


def list_named_droplets(client: Any, name: str, *, page_size: int = 200) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    page = 1
    while True:
        response = client.droplets.list(page=page, per_page=page_size)
        droplets = response.get("droplets")
        if not isinstance(droplets, list):
            raise RuntimeError("invalid_provider_response")
        matches.extend(item for item in droplets if item.get("name") == name)
        if len(droplets) < page_size:
            break
        page += 1
    return matches


def lookup(client: Any, name: str, *, page_size: int = 200) -> dict[str, str]:
    matches = list_named_droplets(client, name, page_size=page_size)
    if not matches:
        return {"state": "missing", "id": "", "ip": ""}
    if len(matches) != 1:
        return {"state": "ambiguous", "id": "", "ip": ""}
    public_ips = [
        network.get("ip_address")
        for network in matches[0].get("networks", {}).get("v4", [])
        if network.get("type") == "public" and network.get("ip_address")
    ]
    if len(public_ips) != 1:
        return {
            "state": "pending" if not public_ips else "ambiguous",
            "id": "",
            "ip": "",
        }
    droplet_id = matches[0].get("id")
    if not isinstance(droplet_id, int) or droplet_id <= 0:
        raise RuntimeError("invalid_provider_identity")
    return {"state": "found", "id": str(droplet_id), "ip": str(public_ips[0])}


def main() -> int:
    token = os.environ.get("DO_API_TOKEN")
    project = (os.environ.get("PROJECT_NAME") or "app").strip() or "app"
    if not token:
        print(json.dumps({"state": "error", "id": "", "ip": ""}, sort_keys=True))
        return 2
    try:
        from pydo import Client

        name = resolve_name(os.environ.get("DO_DROPLET_NAME"), project)
        result = lookup(Client(token=token), name)
    except Exception:
        print(json.dumps({"state": "error", "id": "", "ip": ""}, sort_keys=True))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] in {"found", "missing"} else 4


if __name__ == "__main__":
    raise SystemExit(main())
