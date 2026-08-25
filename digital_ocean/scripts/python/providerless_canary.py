#!/usr/bin/env python3
"""Run the complete preview lifecycle without credentials, network, or provider state."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from digital_ocean.scripts.python.deployment_evidence import EvidenceStore
    from digital_ocean.scripts.python.preview_lease import LeaseStore
    from digital_ocean.scripts.python.preview_orchestrator import PreviewOrchestrator
    from digital_ocean.scripts.python.provider_admission import (
        AdmissionPolicy,
        AdmissionSnapshot,
        ProviderAdmissionController,
    )
except ModuleNotFoundError:
    from deployment_evidence import EvidenceStore
    from preview_lease import LeaseStore
    from preview_orchestrator import PreviewOrchestrator
    from provider_admission import (
        AdmissionPolicy,
        AdmissionSnapshot,
        ProviderAdmissionController,
    )


class ProviderlessFixture:
    """In-memory provider with the same narrow protocol as the live adapter."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.resources: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.dns = {("example.test", "preview", "A"): ["192.0.2.10"]}

    def provision(self, ownership_tag: str) -> dict[str, Any]:
        self.calls.append(("provision", ownership_tag))
        resource = {"id": "fixture-001", "tags": [ownership_tag]}
        self.resources[("digitalocean", "droplet", "fixture-001")] = resource
        return resource

    def bootstrap(self, provider_id: str) -> None:
        self.calls.append(("bootstrap", provider_id))

    def dns_values(self, provider_id: str) -> list[str]:
        self.calls.append(("dns-values", provider_id))
        return ["192.0.2.20"]

    def health(self, provider_id: str) -> bool:
        self.calls.append(("health", provider_id))
        return provider_id == "fixture-001"

    def read_values(self, zone: str, name: str, record_type: str) -> list[str]:
        return list(self.dns.get((zone, name, record_type), []))

    def replace_values(
        self, zone: str, name: str, record_type: str, values: list[str]
    ) -> None:
        self.calls.append(("dns", zone, name, record_type, tuple(values)))
        self.dns[(zone, name, record_type)] = list(values)

    def get_resource(self, provider: str, kind: str, provider_id: str) -> dict | None:
        return self.resources.get((provider, kind, provider_id))

    def delete_resource(self, provider: str, kind: str, provider_id: str) -> None:
        self.calls.append(("delete", provider, kind, provider_id))
        self.resources.pop((provider, kind, provider_id), None)

    def list_owned_resources(self, ownership_tag: str) -> list[dict]:
        return [item for item in self.resources.values() if ownership_tag in item["tags"]]


def _source_commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    value = result.stdout.strip()
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError("providerless canary requires an exact lowercase source commit")
    return value


def _evidence(run_id: str, action: str, source_commit: str, started_at: str) -> dict:
    return {
        "schemaVersion": 1,
        "runId": run_id,
        "leaseId": "lease-providerless-canary",
        "sourceCommit": source_commit,
        "manifestDigest": hashlib.sha256(b"providerless-canary-v1").hexdigest(),
        "action": action,
        "status": "running",
        "startedAt": started_at,
        "finishedAt": None,
        "stages": [],
        "cost": {
            "currency": "USD",
            "ceilingMinorUnits": 1,
            "projectedMinorUnits": 0,
            "actualMinorUnits": 0,
            "withinBudget": True,
        },
        "artifacts": [],
        "failure": None,
    }


def run_canary(repo_root: Path) -> dict[str, Any]:
    source_commit = _source_commit(repo_root)
    started = datetime.now(UTC).replace(microsecond=0)
    times = iter(started + timedelta(seconds=value) for value in range(80))
    timestamp = started.isoformat().replace("+00:00", "Z")
    manifest_digest = hashlib.sha256(b"providerless-canary-v1").hexdigest()
    lease = {
        "schemaVersion": 1,
        "leaseId": "lease-providerless-canary",
        "siteId": "base2-providerless-canary",
        "sourceCommit": source_commit,
        "manifestDigest": manifest_digest,
        "owner": "ci:providerless-canary",
        "state": "planned",
        "createdAt": timestamp,
        "expiresAt": (started + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
        "costPolicy": {"currency": "USD", "maximumMinorUnits": 1},
        "resources": [],
        "dnsMutations": [
            {
                "zone": "example.test",
                "name": "preview",
                "type": "A",
                "previousValues": ["192.0.2.10"],
                "desiredValues": ["192.0.2.20"],
                "state": "planned",
            }
        ],
    }
    provider = ProviderlessFixture()
    with tempfile.TemporaryDirectory(prefix="base2-providerless-canary-") as temp:
        root = Path(temp)
        admission = ProviderAdmissionController(
            root / "admission",
            AdmissionPolicy(
                maximum_active_resources=1,
                minimum_disk_free_bytes=1,
                minimum_memory_available_bytes=1,
            ),
            clock=lambda: started,
            sleep=lambda _delay: None,
        )
        flow = PreviewOrchestrator(
            LeaseStore(root / "leases"),
            EvidenceStore(root / "evidence"),
            provider,
            admission,
            lambda: AdmissionSnapshot(
                active_resources=0,
                provider_quota=1,
                projected_minor_units=0,
                budget_ceiling_minor_units=1,
                disk_free_bytes=1,
                memory_available_bytes=1,
                oom_kills=0,
            ),
            clock=lambda: next(times),
            sleep=lambda _delay: None,
        )
        deployed, deploy_receipt = flow.deploy(
            lease,
            _evidence("run-providerless-deploy", "deploy", source_commit, timestamp),
            certificate_sans={"preview.example.test"},
        )
        calls_after_deploy = len(provider.calls)
        replayed, replay_receipt = flow.deploy(
            lease,
            _evidence("run-providerless-deploy", "deploy", source_commit, timestamp),
            certificate_sans={"preview.example.test"},
        )
        calls_after_replay = len(provider.calls)
        _, update_receipt = flow.update(
            lease["leaseId"],
            _evidence("run-providerless-update", "update", source_commit, timestamp),
        )
        destroyed, rollback_receipt = flow.rollback(
            lease["leaseId"],
            _evidence("run-providerless-rollback", "rollback", source_commit, timestamp),
        )
        assertions = {
            "deployPassed": deploy_receipt["status"] == "passed",
            "updatePassed": update_receipt["status"] == "passed",
            "rollbackPassed": rollback_receipt["status"] == "passed",
            "exactReplayNoProviderCalls": replayed == deployed
            and replay_receipt == deploy_receipt
            and calls_after_replay == calls_after_deploy,
            "leaseDestroyed": destroyed["state"] == "destroyed",
            "dnsRestored": provider.dns[("example.test", "preview", "A")]
            == ["192.0.2.10"],
            "zeroProviderResources": provider.resources == {},
        }
        if not all(assertions.values()):
            raise RuntimeError(f"providerless canary failed: {assertions}")
        return {
            "schemaVersion": 1,
            "status": "passed",
            "sourceCommit": source_commit,
            "provider": "in-memory-fixture",
            "networkRequests": 0,
            "credentialReads": 0,
            "externalProviderMutations": 0,
            "publicDnsMutations": 0,
            "productionCertificates": 0,
            "fixtureCalls": len(provider.calls),
            "assertions": assertions,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args(argv)
    print(json.dumps(run_canary(args.repo_root.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
