#!/usr/bin/env python3
"""Launch one bounded full Base2 preview and bind its exact lifecycle lease."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import stat
import time
from typing import Callable

from digital_ocean.scripts.python.full_preview_dns import migrate_required_records, restore_migration
from digital_ocean.scripts.python.full_preview_policy import canonical_digest, full_preview_policy
from digital_ocean.scripts.python.full_preview_probe import verify_full_preview
from digital_ocean.scripts.python.full_preview_remote import FullPreviewSshBootstrap
from digital_ocean.scripts.python.live_preview_provider import DigitalOceanHttpClient, LivePreviewConfig
from digital_ocean.scripts.python.preview_lease_v2 import FullPreviewLeaseStore, RUN_ID


class FullPreviewLaunchError(RuntimeError):
    pass


def _private(path: Path, label: str) -> str:
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise FullPreviewLaunchError(f"{label} must be an owner-only real file")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise FullPreviewLaunchError(f"{label} is empty")
    return value


def _token(path: Path) -> str:
    payload = json.loads(_private(path, "resolved credential"))
    value = (payload.get("secrets") or {}).get("DO_API_TOKEN") or (payload.get("secrets") or {}).get("DIGITAL_OCEAN_API_TOKEN")
    if not isinstance(value, str) or not value:
        raise FullPreviewLaunchError("DigitalOcean SecretRef resolution is unavailable")
    return value


def _public_ip(row: dict) -> str | None:
    for network in ((row.get("networks") or {}).get("v4") or []):
        if network.get("type") == "public":
            try:
                address = ipaddress.IPv4Address(str(network.get("ip_address") or ""))
            except ValueError:
                continue
            if address.is_global:
                return str(address)
    return None


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def launch(
    *, client, remote, source_archive: Path, ssh_key: Path, source_commit: str,
    profile_digest: str, domain: str, owner_cidr: str, run_id: str,
    probe_username: str, probe_password: str, state_root: Path, ssh_key_id: int,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC), sleep: Callable[[float], None] = time.sleep,
    ttl_minutes: int = 60, maximum_wait_attempts: int = 60,
    probe: Callable = verify_full_preview,
) -> dict:
    policy = full_preview_policy(domain, [owner_cidr], ttl_minutes=ttl_minutes)
    archive_digest = hashlib.sha256(source_archive.read_bytes()).hexdigest()
    if len(source_commit) != 40 or any(ch not in "0123456789abcdef" for ch in source_commit):
        raise FullPreviewLaunchError("exact source commit is invalid")
    if len(profile_digest) != 64 or any(ch not in "0123456789abcdef" for ch in profile_digest):
        raise FullPreviewLaunchError("exact profile digest is invalid")
    if not RUN_ID.fullmatch(run_id):
        raise FullPreviewLaunchError("run ID is invalid")
    if not isinstance(ssh_key_id, int) or ssh_key_id < 1:
        raise FullPreviewLaunchError("existing SSH key ID is required")
    if not 1 <= maximum_wait_attempts <= 60:
        raise FullPreviewLaunchError("wait attempts exceed bounded policy")
    config = LivePreviewConfig(
        source_commit=source_commit, plan_digest=canonical_digest(policy), archive_sha256=archive_digest,
        source_archive=source_archive, ssh_private_key=ssh_key, ssh_key_id=ssh_key_id,
        droplet_name="base2-full-preview", region="fra1", size="s-2vcpu-2gb", image="ubuntu-24-04-x64",
        zone=domain, record_name="admin", fqdn=f"admin.{domain}", admission_tag=run_id,
    ).validate()
    if (client.droplets.list(tag_name=run_id) or {}).get("droplets"):
        raise FullPreviewLaunchError("exact-owned preview already exists")
    started = clock().astimezone(UTC)
    droplet = None
    dns_receipt = None
    try:
        droplet = (client.droplets.create({
            "name": "base2-full-preview", "region": "fra1", "size": "s-2vcpu-2gb",
            "image": "ubuntu-24-04-x64", "ssh_keys": [ssh_key_id], "backups": False, "ipv6": False,
            "monitoring": False, "tags": [run_id, "base2-full-preview"],
        }) or {}).get("droplet") or {}
        provider_id = str(droplet.get("id") or "")
        if not provider_id or run_id not in (droplet.get("tags") or []):
            raise FullPreviewLaunchError("created Droplet lacks exact identity")
        address = None
        for attempt in range(maximum_wait_attempts):
            droplet = (client.droplets.get(int(provider_id)) or {}).get("droplet") or {}
            address = _public_ip(droplet)
            if droplet.get("status") == "active" and address:
                break
            if attempt + 1 < maximum_wait_attempts:
                sleep(5)
        if not address:
            raise FullPreviewLaunchError("bounded Droplet readiness wait exhausted")
        remote.deploy(address, config)
        if remote.health(address, domain) is not True:
            raise FullPreviewLaunchError("direct-address health verification failed")
        dns_receipt = migrate_required_records(client.domains, domain, address)
        probe_receipt = probe(domain, address, username=probe_username, password=probe_password, owner_cidrs=[owner_cidr])
        created_at = str(droplet.get("created_at") or started.isoformat().replace("+00:00", "Z"))
        lease = {
            "schemaVersion": 2, "runId": run_id, "state": "live-verified",
            "armedAt": started.isoformat().replace("+00:00", "Z"),
            "expiresAt": (started + timedelta(minutes=ttl_minutes)).isoformat().replace("+00:00", "Z"),
            "sourceCommit": source_commit, "sourceArchiveSha256": archive_digest,
            "profileId": "base2-obsidian", "profileDigest": profile_digest,
            "droplet": {"id": provider_id, "name": "base2-full-preview", "tags": sorted(droplet.get("tags") or []), "size": "s-2vcpu-2gb", "createdAt": created_at},
            "dnsRecords": dns_receipt["records"], "ownerAdmissionDigest": policy["ownerAdmissionDigest"],
            "certificateMode": "letsencrypt-staging-only", "budgetCeilingUsd": "0.25", "lastError": None,
            "mutationCounts": {"dropletsDeleted": 0, "dnsRecordsDeleted": 0},
        }
        FullPreviewLeaseStore(state_root / "leases").create(lease)
        result = {
            "schemaVersion": 1, "ok": True, "status": "live-verified", "runId": run_id,
            "sourceCommit": source_commit, "profileId": "base2-obsidian", "publicIp": address,
            "domain": domain, "expiresAt": lease["expiresAt"], "routeCount": probe_receipt["routeCount"],
            "dnsRecordCount": len(dns_receipt["records"]), "certificateMode": "letsencrypt-staging-only",
            "secretValuesEmitted": 0,
        }
        _write(state_root / "evidence" / f"{run_id}.json", result)
        return result
    except Exception as exc:
        cleanup_errors = []
        if dns_receipt is not None:
            try:
                restore_migration(client.domains, dns_receipt)
            except Exception as cleanup:
                cleanup_errors.append(type(cleanup).__name__)
        if droplet and droplet.get("id"):
            try:
                client.droplets.delete(int(droplet["id"]))
            except Exception as cleanup:
                cleanup_errors.append(type(cleanup).__name__)
        if cleanup_errors:
            raise FullPreviewLaunchError("launch failed and cleanup requires reconciliation") from exc
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--ssh-private-key", type=Path, required=True)
    parser.add_argument("--ssh-key-id", type=int, required=True)
    parser.add_argument("--operator-auth-file", type=Path, required=True)
    parser.add_argument("--flower-auth-file", type=Path, required=True)
    parser.add_argument("--probe-username-file", type=Path, required=True)
    parser.add_argument("--probe-password-file", type=Path, required=True)
    parser.add_argument("--django-username-file", type=Path, required=True)
    parser.add_argument("--django-email-file", type=Path, required=True)
    parser.add_argument("--django-password-file", type=Path, required=True)
    parser.add_argument("--pgadmin-email-file", type=Path, required=True)
    parser.add_argument("--pgadmin-password-file", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--profile-digest", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--owner-cidr", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--ttl-minutes", type=int, default=60)
    args = parser.parse_args(argv)
    client = DigitalOceanHttpClient(_token(args.credential_file))
    remote = FullPreviewSshBootstrap(
        known_hosts=args.state_root / "known_hosts", owner_cidr=args.owner_cidr,
        operator_auth=args.operator_auth_file, flower_auth=args.flower_auth_file,
        django_username=args.django_username_file, django_email=args.django_email_file,
        django_password=args.django_password_file, pgadmin_email=args.pgadmin_email_file,
        pgadmin_password=args.pgadmin_password_file,
    )
    result = launch(
        client=client, remote=remote, source_archive=args.source_archive, ssh_key=args.ssh_private_key,
        source_commit=args.source_commit, profile_digest=args.profile_digest, domain=args.domain,
        owner_cidr=args.owner_cidr, run_id=args.run_id,
        probe_username=_private(args.probe_username_file, "probe username"),
        probe_password=_private(args.probe_password_file, "probe password"),
        state_root=args.state_root, ssh_key_id=args.ssh_key_id, ttl_minutes=args.ttl_minutes,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
