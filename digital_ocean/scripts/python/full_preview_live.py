#!/usr/bin/env python3
"""Launch one bounded full Base2 preview and bind its exact lifecycle lease."""
from __future__ import annotations

import argparse
from functools import wraps
from datetime import UTC, datetime, timedelta
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import Callable

from digital_ocean.scripts.python.full_preview_dns import migrate_required_records, restore_migration
from digital_ocean.scripts.python.full_preview_expire import LeaseDigitalOceanProvider, bounded_inventory
from digital_ocean.scripts.python.preview_dns_journal import DnsJournal, JournaledDnsProvider
from digital_ocean.scripts.python.full_preview_policy import canonical_digest, full_preview_policy
from digital_ocean.scripts.python.full_preview_probe import verify_full_preview
from digital_ocean.scripts.python.full_preview_remote import FullPreviewSshBootstrap, FullPreviewRemoteError
from digital_ocean.scripts.python.live_preview_provider import DigitalOceanHttpClient, LivePreviewConfig
from digital_ocean.scripts.python.preview_lease_v2 import (
    DNS_RECONCILIATION_REQUIRED, FullPreviewLeaseStore, LeaseV2Conflict, RUN_ID,
)


class FullPreviewLaunchError(RuntimeError):
    pass


DIRECT_HEALTH_ATTEMPTS = 12
DIRECT_HEALTH_INTERVAL_SECONDS = 5


def _private(path: Path, label: str) -> str:
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise FullPreviewLaunchError(f"{label} must be an owner-only real file")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise FullPreviewLaunchError(f"{label} is empty")
    return value


def _owner_identity(path: Path, label: str, *, email: bool = False) -> str:
    value = _private(path, label)
    normalized = value.casefold()
    local, separator, domain = normalized.partition("@")
    forbidden_locals = {"canary", "demo", "fixture", "test"}
    forbidden_domains = {"example.com", "example.net", "example.org", "invalid"}
    if local in forbidden_locals or (email and (not separator or domain in forbidden_domains)):
        raise FullPreviewLaunchError(f"{label} must identify the preview owner, not a fixture")
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


def _record_remote_failure(state_root: Path, run_id: str, source_commit: str,
                           error: FullPreviewRemoteError) -> None:
    """Retain only typed metadata, never remote output or exception messages."""
    if not RUN_ID.fullmatch(run_id):
        raise FullPreviewLaunchError("invalid failure evidence identity")
    # Revalidate attributes rather than trusting mutable exception properties.
    safe = FullPreviewRemoteError("", stage=error.stage, reason=error.reason,
                                  exit_code=error.exit_code)
    payload = {"runId": run_id, "sourceCommit": source_commit, "ok": False,
               "stage": safe.stage, "reason": safe.reason, "exitCode": safe.exit_code,
               "secretValuesEmitted": 0}
    directory = state_root / "evidence"
    directory.mkdir(mode=0o700, exist_ok=True)
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory_fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise FullPreviewLaunchError("unsafe failure evidence directory")
        fd = os.open(f"{run_id}.failure.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(directory_fd)


def _exclusive_launch(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        # One operator account is the supported deployment authority. Different
        # per-run directories still share the domain admission lock.
        domain = str(kwargs["domain"])
        identity = hashlib.sha256(domain.encode()).hexdigest()
        admission = Path.home() / ".local/state/base2-preview-admission" / identity
        with FullPreviewLeaseStore(admission).operation():
            with FullPreviewLeaseStore(kwargs["state_root"] / "leases").operation():
                return function(*args, **kwargs)
    return guarded


@_exclusive_launch
def launch(
    *, client, remote, source_archive: Path, ssh_key: Path, source_commit: str,
    profile_digest: str, domain: str, owner_cidr: str, run_id: str,
    probe_username: str, probe_password: str, state_root: Path, ssh_key_id: int,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC), sleep: Callable[[float], None] = time.sleep,
    ttl_minutes: int = 60, maximum_wait_attempts: int = 60,
    probe: Callable = verify_full_preview, preview_mode: str = 'full',
    schedule: Callable | None = None,
) -> dict:
    if preview_mode not in {'full', 'restricted'}:
        raise FullPreviewLaunchError('invalid preview mode')
    if preview_mode == 'restricted' and getattr(remote, 'preview_mode', None) != 'restricted':
        raise FullPreviewLaunchError('restricted remote mode mismatch')
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
        droplet_name="base2-full-preview", region="fra1", size="s-2vcpu-4gb", image="ubuntu-24-04-x64",
        zone=domain, record_name="admin", fqdn=f"admin.{domain}", admission_tag=run_id,
    ).validate()
    if bounded_inventory(client.droplets.list(tag_name=run_id), "droplets"):
        raise FullPreviewLaunchError("exact-owned preview already exists")
    if bounded_inventory(client.droplets.list(tag_name="base2-full-preview"), "droplets"):
        raise FullPreviewLaunchError("another full preview requires reconciliation before launch")
    started = clock().astimezone(UTC)
    store = FullPreviewLeaseStore(state_root / "leases")
    # Reject all reuse, including destroyed runs; never reset an existing expiry.
    if (store.root / f"{run_id}.json").exists():
        raise LeaseV2Conflict("run ID already has a durable lease")
    lease = {
        "schemaVersion": 2, "runId": run_id, "state": "prepared",
        "armedAt": started.isoformat().replace("+00:00", "Z"),
        "expiresAt": (started + timedelta(minutes=ttl_minutes)).isoformat().replace("+00:00", "Z"),
        "sourceCommit": source_commit, "sourceArchiveSha256": archive_digest,
        "profileId": "base2-obsidian", "profileDigest": profile_digest,
        "droplet": None, "dnsRecords": [],
        "ownerAdmissionDigest": policy["ownerAdmissionDigest"],
        "certificateMode": "letsencrypt-staging-only", "budgetCeilingUsd": "0.25",
        "lastError": None, "mutationCounts": {"dropletsDeleted": 0, "dnsRecordsDeleted": 0},
    }
    store.create(lease)
    if schedule is not None:
        schedule(lease)  # No create is permitted if persistent cleanup cannot arm.
    droplet = None
    dns_receipt = None
    dns_journal = None
    dns_provider = None
    def require_unexpired():
        if clock().astimezone(UTC) >= started + timedelta(minutes=ttl_minutes):
            raise FullPreviewLaunchError("preview lease expired during launch")
    try:
        require_unexpired()
        droplet = (client.droplets.create({
            "name": "base2-full-preview", "region": "fra1", "size": "s-2vcpu-4gb",
            "image": "ubuntu-24-04-x64", "ssh_keys": [ssh_key_id], "backups": False, "ipv6": False,
            "monitoring": False, "tags": [run_id, "base2-full-preview"],
        }) or {}).get("droplet") or {}
        provider_id = str(droplet.get("id") or "")
        if not provider_id or run_id not in (droplet.get("tags") or []):
            raise FullPreviewLaunchError("created Droplet lacks exact identity")
        lease["droplet"] = {
            "id": provider_id, "name": str(droplet.get("name") or ""),
            "tags": sorted(droplet.get("tags") or []),
            "size": str((droplet.get("size") or {}).get("slug") or droplet.get("size_slug") or ""),
            "createdAt": str(droplet.get("created_at") or ""),
        }
        lease["state"] = "compute-bound"
        store.replace(lease)
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
        require_unexpired()
        direct_healthy = False
        for attempt in range(DIRECT_HEALTH_ATTEMPTS):
            if remote.health(address, domain) is True:
                direct_healthy = True
                break
            if attempt + 1 < DIRECT_HEALTH_ATTEMPTS:
                sleep(DIRECT_HEALTH_INTERVAL_SECONDS)
        if not direct_healthy:
            raise FullPreviewLaunchError("direct-address health verification failed")
        require_unexpired()
        # Fail closed if interrupted anywhere inside the DNS transaction. A
        # compute-only lease must not masquerade as complete cleanup afterward.
        lease["lastError"] = DNS_RECONCILIATION_REQUIRED
        store.replace(lease)
        dns_journal = DnsJournal(store.root / f"{run_id}.dns-journal", run_id, domain)
        dns_journal.create()
        dns_provider = JournaledDnsProvider(client.domains, dns_journal)
        dns_receipt = migrate_required_records(dns_provider, domain, address)
        dns_journal.phase("committed")
        lease["dnsRecords"] = dns_receipt["records"]
        lease["state"] = "dns-bound"
        lease["lastError"] = None
        store.replace(lease)
        probe_receipt = probe(domain, address, username=probe_username, password=probe_password, owner_cidrs=[owner_cidr])
        require_unexpired()
        lease["dnsRecords"] = dns_receipt["records"]
        lease["state"] = "live-verified"
        store.replace(lease)
        result = {
            'previewMode': preview_mode,
            'mediaAcceptance': 'blocked' if preview_mode == 'restricted' else 'pending',
            "schemaVersion": 1, "ok": True, "status": "live-verified", "runId": run_id,
            "sourceCommit": source_commit, "profileId": "base2-obsidian", "publicIp": address,
            "domain": domain, "expiresAt": lease["expiresAt"], "routeCount": probe_receipt["routeCount"],
            "dnsRecordCount": len(dns_receipt["records"]), "certificateMode": "letsencrypt-staging-only",
            "secretValuesEmitted": 0,
        }
        _write(state_root / "evidence" / f"{run_id}.json", result)
        return result
    except Exception as exc:
        if isinstance(exc, FullPreviewRemoteError):
            try:
                _record_remote_failure(state_root, run_id, source_commit, exc)
            except Exception:
                # Evidence storage must never prevent cleanup or mask the cause.
                print("full-preview-failure-evidence:unavailable", file=sys.stderr)
        # Persist only an exception class; messages can contain credentials.
        # Reload the last valid checkpoint, not a partially validated response.
        failed_lease = store.load(run_id)
        failed_lease["state"] = "blocked"
        if failed_lease["lastError"] != DNS_RECONCILIATION_REQUIRED:
            failed_lease["lastError"] = type(exc).__name__
        store.replace(failed_lease)
        cleanup_errors = []
        if dns_receipt is not None:
            try:
                failed_lease["lastError"] = DNS_RECONCILIATION_REQUIRED
                store.replace(failed_lease)
                dns_journal.phase("restoring")
                restore_migration(dns_provider, dns_receipt)
                dns_journal.phase("restored")
                failed_lease["dnsRecords"] = []
                failed_lease["lastError"] = type(exc).__name__
                store.replace(failed_lease)
            except Exception as cleanup:
                cleanup_errors.append(type(cleanup).__name__)
        bound = failed_lease["droplet"]
        if bound is not None:
            try:
                provider = LeaseDigitalOceanProvider(client)
                current = provider.get_droplet(bound["id"])
                if current is not None and current != bound:
                    raise LeaseV2Conflict("cleanup compute identity changed")
                if current is not None:
                    provider.delete_droplet(bound["id"])
            except Exception as cleanup:
                cleanup_errors.append(type(cleanup).__name__)
        elif droplet:
            cleanup_errors.append("UnboundComputeIdentity")
        if cleanup_errors:
            raise FullPreviewLaunchError("launch failed and cleanup requires reconciliation") from exc
        raise


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--application-owner-file", type=Path)
    parser.add_argument("--mail-trial-file", type=Path)
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
    parser.add_argument('--preview-mode', choices=['full', 'restricted'], default='full')
    args = parser.parse_args(argv)
    if args.mail_trial_file is not None:
        from digital_ocean.scripts.python.mail_trial_config import load_trial
        load_trial(args.mail_trial_file, args.domain, ttl_minutes=args.ttl_minutes)
        from digital_ocean.scripts.python.persistent_mail_dns import main as mail_dns_main
        if mail_dns_main([
            '--config', str(Path(__file__).resolve().parents[2] / 'config/woodkilldev-resend-dns.json'),
            '--credential-file', str(args.credential_file),
            '--state-root', str(Path.home() / '.local/state/base2-mail-dns'), '--apply',
        ]) != 0:
            raise FullPreviewLaunchError('mail DNS prerequisite failed before provisioning')
    from digital_ocean.scripts.python.preview_workstation_schedule import install_schedule
    probe_username = _owner_identity(args.probe_username_file, "probe username")
    _owner_identity(args.django_username_file, "Django username")
    _owner_identity(args.django_email_file, "Django email", email=True)
    _owner_identity(args.pgadmin_email_file, "pgAdmin email", email=True)
    client = DigitalOceanHttpClient(_token(args.credential_file))
    remote = FullPreviewSshBootstrap(
        known_hosts=args.state_root / "known_hosts", owner_cidr=args.owner_cidr,
        operator_auth=args.operator_auth_file, flower_auth=args.flower_auth_file,
        django_username=args.django_username_file, django_email=args.django_email_file,
        django_password=args.django_password_file, pgadmin_email=args.pgadmin_email_file,
        pgadmin_password=args.pgadmin_password_file,
        application_owner=args.application_owner_file,
        mail_trial=args.mail_trial_file,
        preview_mode=args.preview_mode,
    )
    result = launch(
        client=client, remote=remote, source_archive=args.source_archive, ssh_key=args.ssh_private_key,
        source_commit=args.source_commit, profile_digest=args.profile_digest, domain=args.domain,
        owner_cidr=args.owner_cidr, run_id=args.run_id,
        probe_username=probe_username,
        probe_password=_private(args.probe_password_file, "probe password"),
        state_root=args.state_root, ssh_key_id=args.ssh_key_id, ttl_minutes=args.ttl_minutes,
        preview_mode=args.preview_mode,
        schedule=lambda lease: install_schedule(
            lease, repo=Path(__file__).resolve().parents[3], python=Path(sys.executable),
            state_root=args.state_root / "leases", credential_file=args.credential_file,
        ),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except Exception as exc:
        # Provider exceptions can include URLs, headers or secrets. Keep detailed
        # lifecycle state private and expose only a type plus recovery direction.
        print(json.dumps({"ok": False, "error": type(exc).__name__,
                          "nextAction": "Inspect the private lease and reconcile before retrying.",
                          "secretValuesEmitted": 0}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
