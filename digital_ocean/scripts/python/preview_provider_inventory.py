#!/usr/bin/env python3
"""Read-only exact-owned DigitalOcean inventory reconciliation."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol


class ProviderInventoryError(RuntimeError):
    def __init__(self, code: str, message: str, *, retry_after: int | None = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class DropletClient(Protocol):
    def list(self, **kwargs) -> dict: ...


def reconcile_provider_inventory(
    droplets: DropletClient,
    lease_inventory: dict,
    *,
    maximum_attempts: int = 2,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict:
    if maximum_attempts not in {1, 2}:
        raise ProviderInventoryError(
            "LIFECYCLE_EXTERNAL_FAILURE", "provider retry policy is invalid"
        )
    attempts = 0
    while True:
        attempts += 1
        try:
            rows = (droplets.list(tag_name="base2-full-preview") or {}).get("droplets") or []
            break
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            retry = getattr(exc, "retry_after", None)
            bounded_retry = retry if isinstance(retry, int) and 0 <= retry <= 5 else None
            if status == 429 and attempts < maximum_attempts and bounded_retry is not None:
                sleeper(float(bounded_retry))
                continue
            if status == 429:
                raise ProviderInventoryError(
                    "PROVIDER_RATE_LIMITED",
                    "provider inventory is rate limited",
                    retry_after=retry if isinstance(retry, int) and 0 <= retry <= 3600 else None,
                ) from exc
            raise ProviderInventoryError(
                "LIFECYCLE_EXTERNAL_FAILURE", "provider inventory failed"
            ) from exc
    lease_by_droplet = {
        str(row["dropletId"]): row
        for row in lease_inventory.get("leases", [])
        if row.get("dropletId")
    }
    resources = []
    orphaned = []
    for row in rows:
        resource = {
            "id": str(row.get("id") or ""),
            "name": str(row.get("name") or ""),
            "status": str(row.get("status") or ""),
            "tags": sorted(str(tag) for tag in (row.get("tags") or [])),
        }
        resources.append(resource)
        lease = lease_by_droplet.get(resource["id"])
        if lease is None or lease["effectiveState"] == "destroyed":
            orphaned.append(resource["id"])
    resources.sort(key=lambda item: item["id"])
    unresolved = lease_inventory.get("unresolvedRunIds") or []
    code = "OK" if not resources and not unresolved else "LEASE_CONFLICT"
    return {
        "schemaVersion": 1,
        "ok": code == "OK",
        "code": code,
        "ownedDropletCount": len(resources),
        "ownedDroplets": resources,
        "orphanedDropletIds": sorted(orphaned),
        "unresolvedRunIds": sorted(unresolved),
        "providerActions": 0,
        "attempts": attempts,
        "secretValuesEmitted": 0,
    }
