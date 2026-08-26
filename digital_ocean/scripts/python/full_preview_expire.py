#!/usr/bin/env python3
"""Run the unified exact-identity expiry/approved-teardown operation."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import stat

from digital_ocean.scripts.python.live_preview_provider import DigitalOceanHttpClient
from digital_ocean.scripts.python.preview_lease_v2 import FullPreviewLeaseStore, teardown_full_preview


class ExpiryError(RuntimeError):
    pass


def _token(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ExpiryError("credential file must be an owner-only real file")
    value = json.loads(path.read_text(encoding="utf-8"))
    token = (value.get("secrets") or {}).get("DO_API_TOKEN") or (value.get("secrets") or {}).get("DIGITAL_OCEAN_API_TOKEN")
    if not isinstance(token, str) or not token:
        raise ExpiryError("DigitalOcean SecretRef resolution is unavailable")
    return token


class LeaseDigitalOceanProvider:
    def __init__(self, client):
        self.client = client

    @staticmethod
    def _droplet(row: dict) -> dict:
        return {
            "id": str(row.get("id") or ""), "name": str(row.get("name") or ""),
            "tags": sorted(str(item) for item in (row.get("tags") or [])),
            "size": str((row.get("size") or {}).get("slug") or row.get("size_slug") or ""),
            "createdAt": str(row.get("created_at") or ""),
        }

    def get_droplet(self, resource_id: str) -> dict | None:
        try:
            row = (self.client.droplets.get(int(resource_id)) or {}).get("droplet")
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                return None
            raise
        return self._droplet(row) if row else None

    def delete_droplet(self, resource_id: str) -> None:
        self.client.droplets.delete(int(resource_id))

    def list_owned_droplets(self, run_id: str) -> list[dict]:
        rows = (self.client.droplets.list(tag_name=run_id) or {}).get("droplets") or []
        return [self._droplet(row) for row in rows]

    def get_dns_record(self, domain: str, record_id: str) -> dict | None:
        rows = (self.client.domains.list_records(domain) or {}).get("domain_records") or []
        for row in rows:
            if str(row.get("id")) == str(record_id):
                return {"id": str(row["id"]), "domain": domain, "type": str(row["type"]), "name": str(row["name"]), "value": str(row["data"]), "state": "bound"}
        return None

    def delete_dns_record(self, domain: str, record_id: str) -> None:
        self.client.domains.delete_record(domain, int(record_id))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--early-approved", action="store_true")
    args = parser.parse_args(argv)
    client = DigitalOceanHttpClient(_token(args.credential_file))
    lease = teardown_full_preview(
        FullPreviewLeaseStore(args.state_root), LeaseDigitalOceanProvider(client), args.run_id,
        now=datetime.now(UTC), early_approved=args.early_approved,
    )
    print(json.dumps({"ok": lease["state"] == "destroyed", "runId": lease["runId"], "state": lease["state"], "mutationCounts": lease["mutationCounts"], "secretValuesEmitted": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
