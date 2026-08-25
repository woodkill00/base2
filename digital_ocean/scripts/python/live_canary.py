#!/usr/bin/env python3
"""Run the exact approved three-trial Feature 093 live canary."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import time
from typing import Any, Callable

from digital_ocean.scripts.python.deployment_evidence import EvidenceStore
from digital_ocean.scripts.python.live_canary_preflight import (
    BINDING_FIELDS,
    binding_digest,
)
from digital_ocean.scripts.python.live_preview_provider import (
    DigitalOceanHttpClient,
    LiveDigitalOceanProvider,
    LivePreviewConfig,
)
from digital_ocean.scripts.python.live_remote_bootstrap import SshComposeBootstrap
from digital_ocean.scripts.python.preview_lease import LeaseStore
from digital_ocean.scripts.python.preview_orchestrator import PreviewOrchestrator
from digital_ocean.scripts.python.provider_admission import (
    AdmissionPolicy,
    AdmissionSnapshot,
    ProviderAdmissionController,
)


class LiveCanaryError(RuntimeError):
    pass


def _private_file(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise LiveCanaryError(f"{label} must be a private real file")
    if stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) & 0o077:
        raise LiveCanaryError(f"{label} permissions are unsafe")


def validate_plan(plan: dict[str, Any], source_archive: Path) -> dict[str, Any]:
    if plan.get("schemaVersion") != 1 or plan.get("status") != "approval-required":
        raise LiveCanaryError("approved plan envelope is invalid")
    try:
        binding = {key: plan[key] for key in BINDING_FIELDS}
    except KeyError as exc:
        raise LiveCanaryError("approved plan is missing a binding field") from exc
    if binding_digest(binding) != plan.get("planDigest"):
        raise LiveCanaryError("approved plan digest does not match its binding")
    if binding["trialCount"] != 3 or binding["maximumConcurrentDroplets"] != 1:
        raise LiveCanaryError("live canary requires exactly three sequential trials")
    if not 1 <= binding["leaseMinutesPerTrial"] <= 15:
        raise LiveCanaryError("lease duration exceeds the approved limit")
    if not 1 <= binding["totalCostCeilingMinorUnits"] <= 100:
        raise LiveCanaryError("total cost ceiling exceeds policy")
    if not 1 <= binding["hourlyCostMinorUnitsCeiling"] <= 100:
        raise LiveCanaryError("hourly cost ceiling exceeds policy")
    if binding["certificateMode"] != "letsencrypt-staging-only":
        raise LiveCanaryError("production certificate mode is forbidden")
    mutations = binding["dnsMutations"]
    if not isinstance(mutations, list) or len(mutations) != 1:
        raise LiveCanaryError("exactly one DNS mutation is required")
    if binding["certificateSans"] != [mutations[0].get("fqdn")]:
        raise LiveCanaryError("certificate name differs from exact DNS mutation")
    if not source_archive.is_file() or source_archive.is_symlink():
        raise LiveCanaryError("source archive must be a real file")
    actual_archive = hashlib.sha256(source_archive.read_bytes()).hexdigest()
    if actual_archive != binding["sourceArchiveSha256"]:
        raise LiveCanaryError("source archive differs from approved digest")
    return binding


def load_token(path: Path) -> str:
    _private_file(path, "resolved credential")
    payload = json.loads(path.read_text(encoding="utf-8"))
    secrets = payload.get("secrets") or {}
    token = secrets.get("DO_API_TOKEN") or secrets.get("DIGITAL_OCEAN_API_TOKEN")
    if not isinstance(token, str) or not token:
        raise LiveCanaryError("resolved DigitalOcean credential is unavailable")
    return token


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _evidence(
    run_id: str,
    lease_id: str,
    binding: dict[str, Any],
    action: str,
    started: datetime,
    projected_minor_units: int,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "runId": run_id,
        "leaseId": lease_id,
        "sourceCommit": binding["sourceCommit"],
        "manifestDigest": binding_digest(binding),
        "action": action,
        "status": "running",
        "startedAt": _timestamp(started),
        "finishedAt": None,
        "stages": [],
        "cost": {
            "currency": binding["currency"],
            "ceilingMinorUnits": binding["totalCostCeilingMinorUnits"],
            "projectedMinorUnits": projected_minor_units,
            "actualMinorUnits": 0,
            "withinBudget": True,
        },
        "artifacts": [],
        "failure": None,
    }


def _memory_available() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def run_canaries(
    plan: dict[str, Any],
    *,
    token: str,
    source_archive: Path,
    ssh_private_key: Path,
    ssh_key_id: int,
    state_root: Path,
    client_factory: Callable[[str], Any] = DigitalOceanHttpClient,
    remote_factory: Callable[[Path], Any] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    binding = validate_plan(plan, source_archive)
    _private_file(ssh_private_key, "SSH private key")
    last_observed: datetime | None = None

    def observed_clock() -> datetime:
        nonlocal last_observed
        observed = clock()
        if last_observed is not None and observed < last_observed:
            return last_observed
        last_observed = observed
        return observed

    state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_root.chmod(0o700)
    client = client_factory(token)
    trial_receipts = []
    total_cost = 0
    mutation = binding["dnsMutations"][0]
    record_name = mutation["name"]
    fqdn = mutation["fqdn"]

    if remote_factory is None:
        remote_factory = lambda known_hosts: SshComposeBootstrap(
            known_hosts=known_hosts, sleep=sleep
        )

    for trial in range(1, binding["trialCount"] + 1):
        trial_root = state_root / f"trial-{trial}"
        trial_root.mkdir(mode=0o700)
        remote = remote_factory(trial_root / "known_hosts")
        config = LivePreviewConfig(
            source_commit=binding["sourceCommit"],
            plan_digest=plan["planDigest"],
            archive_sha256=binding["sourceArchiveSha256"],
            source_archive=source_archive,
            ssh_private_key=ssh_private_key,
            ssh_key_id=ssh_key_id,
            droplet_name=binding["dropletName"],
            region=binding["region"],
            size=binding["size"],
            image=binding["image"],
            zone=binding["dnsZone"],
            record_name=record_name,
            fqdn=fqdn,
            admission_tag=binding["ownershipNamespace"],
        )
        provider = LiveDigitalOceanProvider(client, config, remote, sleep=sleep)
        if provider.list_owned_resources(binding["ownershipNamespace"]):
            raise LiveCanaryError("admission found an existing canary resource")
        previous_values = provider.read_values(binding["dnsZone"], record_name, "A")
        if previous_values:
            raise LiveCanaryError("exact canary DNS record is not absent")

        started = observed_clock()
        lease_id = f"lease-f093-{binding['sourceCommit'][:8]}-t{trial}"
        site_id = f"base2-f093-t{trial}"
        projected = math.ceil(
            binding["hourlyCostMinorUnitsCeiling"]
            * binding["leaseMinutesPerTrial"]
            / 60
        )
        admission = ProviderAdmissionController(
            trial_root / "admission",
            AdmissionPolicy(
                maximum_active_resources=1,
                minimum_disk_free_bytes=100 * 1024 * 1024,
                minimum_memory_available_bytes=100 * 1024 * 1024,
            ),
            clock=observed_clock,
            sleep=sleep,
        )
        lease_store = LeaseStore(trial_root / "leases")

        def competing_resources() -> int:
            rows = provider.list_owned_resources(binding["ownershipNamespace"])
            current_ids: set[str] = set()
            if lease_store.exists(lease_id):
                current_ids = {
                    item["providerId"] for item in lease_store.load(lease_id)["resources"]
                }
            return sum(1 for row in rows if str(row.get("id") or "") not in current_ids)

        flow = PreviewOrchestrator(
            lease_store,
            EvidenceStore(trial_root / "evidence"),
            provider,
            admission,
            lambda: AdmissionSnapshot(
                active_resources=competing_resources(),
                provider_quota=1,
                projected_minor_units=projected,
                budget_ceiling_minor_units=binding["totalCostCeilingMinorUnits"],
                disk_free_bytes=shutil.disk_usage(state_root).free,
                memory_available_bytes=_memory_available(),
                oom_kills=0,
            ),
            clock=observed_clock,
            sleep=sleep,
        )
        lease_payload = {
            "schemaVersion": 1,
            "leaseId": lease_id,
            "siteId": site_id,
            "sourceCommit": binding["sourceCommit"],
            "manifestDigest": plan["planDigest"],
            "owner": f"owner:approved:{plan['planDigest'][:16]}",
            "state": "planned",
            "createdAt": _timestamp(started),
            "expiresAt": _timestamp(
                started + timedelta(minutes=binding["leaseMinutesPerTrial"])
            ),
            "costPolicy": {
                "currency": binding["currency"],
                "maximumMinorUnits": binding["totalCostCeilingMinorUnits"],
            },
            "resources": [],
            "dnsMutations": [
                {
                    "zone": binding["dnsZone"],
                    "name": record_name,
                    "type": "A",
                    "previousValues": [],
                    "desiredValues": [],
                    "state": "planned",
                }
            ],
        }
        deploy_receipt = None
        rollback_receipt = None
        started_monotonic = monotonic()
        try:
            lease, deploy_receipt = flow.deploy(
                lease_payload,
                _evidence(
                    f"run-f093-{binding['sourceCommit'][:8]}-t{trial}-deploy",
                    lease_id,
                    binding,
                    "deploy",
                    started,
                    projected,
                ),
                certificate_sans={fqdn},
            )
            if lease["state"] != "healthy" or not provider.health(
                lease["resources"][0]["providerId"]
            ):
                raise LiveCanaryError("post-deploy health verification failed")
        finally:
            if flow.leases.exists(lease_id) and flow.leases.load(lease_id)["state"] != "destroyed":
                elapsed = max(0.0, monotonic() - started_monotonic)
                actual_cost = max(
                    1,
                    math.ceil(
                        binding["hourlyCostMinorUnitsCeiling"] * elapsed / 3600
                    ),
                )
                total_cost += actual_cost
                _lease, rollback_receipt = flow.rollback(
                    lease_id,
                    _evidence(
                        f"run-f093-{binding['sourceCommit'][:8]}-t{trial}-rollback",
                        lease_id,
                        binding,
                        "rollback",
                        observed_clock(),
                        projected,
                    ),
                    actual_minor_units=actual_cost,
                )
        if total_cost > binding["totalCostCeilingMinorUnits"]:
            raise LiveCanaryError("observed cost estimate exceeded approved ceiling")
        if provider.list_owned_resources(binding["ownershipNamespace"]):
            raise LiveCanaryError("trial teardown left a provider resource")
        if provider.read_values(binding["dnsZone"], record_name, "A") != []:
            raise LiveCanaryError("trial teardown did not restore DNS absence")
        trial_receipts.append(
            {
                "trial": trial,
                "leaseId": lease_id,
                "deployReceiptDigest": hashlib.sha256(
                    json.dumps(deploy_receipt, sort_keys=True).encode()
                ).hexdigest(),
                "rollbackReceiptDigest": hashlib.sha256(
                    json.dumps(rollback_receipt, sort_keys=True).encode()
                ).hexdigest(),
                "state": "destroyed",
                "dnsRestored": True,
                "zeroProviderResources": True,
            }
        )

    result = {
        "schemaVersion": 1,
        "status": "passed",
        "sourceCommit": binding["sourceCommit"],
        "planDigest": plan["planDigest"],
        "trialCount": len(trial_receipts),
        "trials": trial_receipts,
        "estimatedCostMinorUnits": total_cost,
        "costCeilingMinorUnits": binding["totalCostCeilingMinorUnits"],
        "certificateMode": "letsencrypt-staging-only",
        "dnsRestored": True,
        "zeroProviderResources": True,
        "secretValuesEmitted": 0,
    }
    temporary = state_root / "result.json.tmp"
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, state_root / "result.json")
    print(json.dumps(result, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--resolved-credential", type=Path)
    parser.add_argument("--ssh-private-key", type=Path, required=True)
    parser.add_argument("--ssh-key-id", type=int, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    binding = validate_plan(plan, args.source_archive)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "validated-no-network",
                    "sourceCommit": binding["sourceCommit"],
                    "planDigest": plan["planDigest"],
                    "mutationSent": False,
                    "secretValuesEmitted": 0,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.resolved_credential is None:
        raise LiveCanaryError("resolved credential is required for a live run")
    run_canaries(
        plan,
        token=load_token(args.resolved_credential),
        source_archive=args.source_archive,
        ssh_private_key=args.ssh_private_key,
        ssh_key_id=args.ssh_key_id,
        state_root=args.state_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
