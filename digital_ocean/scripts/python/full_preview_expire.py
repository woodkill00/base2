#!/usr/bin/env python3
"""Run the unified exact-identity expiry/approved-teardown operation."""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from digital_ocean.scripts.python.live_preview_provider import DigitalOceanHttpClient
from digital_ocean.scripts.python.preview_lease_v2 import (
    RUN_ID,
    FullPreviewLeaseStore,
    teardown_full_preview,
)


class ExpiryError(RuntimeError):
    pass


def bounded_inventory(payload, field):
    if (not isinstance(payload, dict) or not isinstance(payload.get(field), list)
            or len(payload[field]) > 1000
            or not all(isinstance(row, dict) for row in payload[field])
            or ((payload.get("links") or {}).get("pages") or {}).get("next")):
        raise ExpiryError("provider inventory incomplete or unbounded")
    return payload[field]


def _token(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ExpiryError("credential file must be an owner-only real file")
    value = json.loads(path.read_text(encoding="utf-8"))
    token = (value.get("secrets") or {}).get("DO_API_TOKEN") or (value.get("secrets") or {}).get(
        "DIGITAL_OCEAN_API_TOKEN"
    )
    if not isinstance(token, str) or not token:
        raise ExpiryError("DigitalOcean SecretRef resolution is unavailable")
    return token


class LeaseDigitalOceanProvider:
    def __init__(self, client):
        self.client = client

    @staticmethod
    def _droplet(row: dict) -> dict:
        return {
            "id": str(row.get("id") or ""),
            "name": str(row.get("name") or ""),
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
        rows = bounded_inventory(self.client.droplets.list(tag_name=run_id), "droplets")
        return [self._droplet(row) for row in rows]

    def get_dns_record(self, domain: str, record_id: str) -> dict | None:
        rows = bounded_inventory(self.client.domains.list_records(domain), "domain_records")
        for row in rows:
            if str(row.get("id")) == str(record_id):
                return {
                    "id": str(row["id"]),
                    "domain": domain,
                    "type": str(row["type"]),
                    "name": str(row["name"]),
                    "value": str(row["data"]),
                    "state": "bound",
                }
        return None

    def delete_dns_record(self, domain: str, record_id: str) -> None:
        self.client.domains.delete_record(domain, int(record_id))


def scan_expired_previews(
    state_root: Path, provider, *, now: datetime, maximum_leases: int = 128
) -> dict:
    """Reconcile every durable expired lease through its exact-owned teardown."""
    if now.tzinfo is None or not 1 <= maximum_leases <= 512:
        raise ExpiryError("expiry scan configuration is invalid")
    if state_root.is_symlink() or not state_root.is_dir():
        raise ExpiryError("lease root must be an existing private directory")
    paths = sorted(state_root.glob("*.json"))
    if len(paths) > maximum_leases:
        raise ExpiryError("lease inventory exceeds the bounded scan capacity")
    store = FullPreviewLeaseStore(state_root)
    destroyed: list[str] = []
    pending: list[str] = []
    for path in paths:
        if path.is_symlink() or not RUN_ID.fullmatch(path.stem):
            raise ExpiryError("lease inventory contains an unsafe member")
        lease = store.load(path.stem)
        if lease["state"] == "destroyed":
            continue
        expiry = datetime.fromisoformat(lease["expiresAt"].replace("Z", "+00:00"))
        if now.astimezone(UTC) < expiry.astimezone(UTC):
            pending.append(path.stem)
            continue
        result = teardown_full_preview(store, provider, path.stem, now=now)
        if result["state"] != "destroyed":
            raise ExpiryError("expired lease did not reach a terminal state")
        destroyed.append(path.stem)
    return {
        "ok": True,
        "scanned": len(paths),
        "destroyed": destroyed,
        "pending": pending,
        "secretValuesEmitted": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-id")
    target.add_argument("--scan", action="store_true")
    target.add_argument("--reconcile", metavar="RUN_ID")
    parser.add_argument("--domain")
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--early-approved", action="store_true")
    parser.add_argument("--stop-timer-on-success", action="store_true")
    args = parser.parse_args(argv)
    if args.stop_timer_on_success and not args.run_id:
        raise ExpiryError("timer completion requires one exact run")
    if args.stop_timer_on_success:
        lease = FullPreviewLeaseStore(args.state_root).load(args.run_id)
        if lease["state"] == "destroyed":
            _stop_timer(args.run_id)
            print(json.dumps({"ok": True, "runId": args.run_id, "state": "destroyed",
                              "mutationSent": False, "secretValuesEmitted": 0}, sort_keys=True))
            return 0
    client = DigitalOceanHttpClient(_token(args.credential_file))
    provider = LeaseDigitalOceanProvider(client)
    if args.reconcile:
        if args.early_approved or not args.domain:
            raise ExpiryError("reconciliation requires domain and never accepts early approval")
        from digital_ocean.scripts.python.preview_dns_journal import DnsJournal, reconcile_dns
        store = FullPreviewLeaseStore(args.state_root)
        with store.operation():
            lease = store.load(args.reconcile)
            rows = provider.list_owned_droplets(args.reconcile)
            if len(rows) > 16:
                raise ExpiryError("reconciliation inventory exceeds bound")
            journal = DnsJournal(store.root / f"{args.reconcile}.dns-journal", args.reconcile, args.domain)
            result = {
                "runId": args.reconcile, "state": lease["state"],
                "computeCandidateIds": [row["id"] for row in rows],
                "dns": reconcile_dns(journal, client.domains) if journal.path.exists() else None,
                "mutationSent": False, "requiresOwnerReconciliation": True,
                "secretValuesEmitted": 0,
            }
    elif args.scan:
        if args.early_approved:
            raise ExpiryError("early approval is invalid for an automatic scan")
        result = scan_expired_previews(args.state_root, provider, now=datetime.now(UTC))
    else:
        lease = teardown_full_preview(
            FullPreviewLeaseStore(args.state_root),
            provider,
            args.run_id,
            now=datetime.now(UTC),
            early_approved=args.early_approved,
        )
        result = {
            "ok": lease["state"] == "destroyed",
            "runId": lease["runId"],
            "state": lease["state"],
            "mutationCounts": lease["mutationCounts"],
            "secretValuesEmitted": 0,
        }
    print(json.dumps(result, sort_keys=True))
    if args.stop_timer_on_success and result.get("state") == "destroyed":
        _stop_timer(args.run_id)
    return 0


def _stop_timer(run_id):
    if not RUN_ID.fullmatch(run_id):
        raise ExpiryError("invalid timer identity")
    result = subprocess.run(["systemctl", "--user", "disable", "--now",
                             f"base2-preview-{run_id}-expiry.timer"],
                            capture_output=True, text=True, check=False, timeout=20)
    if result.returncode:
        raise ExpiryError("terminal cleanup timer could not be disabled")


if __name__ == "__main__":
    raise SystemExit(main())
