#!/usr/bin/env python3
"""Lease-bound preview teardown; never deletes by mutable name."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Protocol

try:
    from pydo import Client
except ModuleNotFoundError:  # Optional: only the legacy standalone CLI needs pydo.
    Client = None

try:
    from digital_ocean.scripts.python.deploy_config import load_deploy_config
    from digital_ocean.scripts.python.deployment_evidence import EvidenceRun, EvidenceStore
    from digital_ocean.scripts.python.preview_lease import LeaseStore
except ModuleNotFoundError:
    from deploy_config import load_deploy_config
    from deployment_evidence import EvidenceRun, EvidenceStore
    from preview_lease import LeaseStore


class TeardownConflict(RuntimeError):
    """Remote identity does not match exact durable ownership evidence."""


class Provider(Protocol):
    def get_resource(self, provider: str, kind: str, provider_id: str) -> dict | None: ...
    def delete_resource(self, provider: str, kind: str, provider_id: str) -> None: ...
    def list_owned_resources(self, ownership_tag: str) -> list[dict]: ...


def _provider_call(operation, *, attempts: int, delay: float, sleep) -> Any:
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            retryable = status == 429 or (isinstance(status, int) and 500 <= status <= 599)
            if not retryable or attempt == attempts:
                raise
            sleep(delay)
    raise AssertionError("bounded provider call did not terminate")


def teardown_lease(
    store: LeaseStore,
    provider: Provider,
    lease_id: str,
    *,
    provider_attempts: int = 3,
    zero_verify_attempts: int = 6,
    retry_delay: float = 1.0,
    sleep=time.sleep,
) -> dict[str, Any]:
    if provider_attempts < 1 or zero_verify_attempts < 1:
        raise ValueError("attempt limits must be positive")
    lease = store.load(lease_id)
    if lease["state"] == "destroyed":
        return {"leaseId": lease_id, "state": "destroyed", "deletedProviderIds": []}
    if any(item["state"] != "restored" for item in lease["dnsMutations"]):
        raise TeardownConflict("DNS mutations require the transactional restoration path")
    if lease["state"] not in {"teardown_due", "destroying"}:
        lease = store.transition(lease_id, "teardown_due")
    if lease["state"] != "destroying":
        lease = store.transition(lease_id, "destroying")

    compared: list[tuple[dict, dict]] = []
    for resource in lease["resources"]:
        remote = _provider_call(
            lambda resource=resource: provider.get_resource(
                resource["provider"], resource["kind"], resource["providerId"]
            ),
            attempts=provider_attempts,
            delay=retry_delay,
            sleep=sleep,
        )
        if remote is None:
            continue
        remote_id = str(remote.get("id", ""))
        tags = remote.get("tags")
        if (
            remote_id != resource["providerId"]
            or not isinstance(tags, list)
            or resource["ownershipTag"] not in tags
        ):
            raise TeardownConflict("remote resource ownership does not match lease")
        compared.append((resource, remote))

    deleted: list[str] = []
    for resource, _remote in compared:
        _provider_call(
            lambda resource=resource: provider.delete_resource(
                resource["provider"], resource["kind"], resource["providerId"]
            ),
            attempts=provider_attempts,
            delay=retry_delay,
            sleep=sleep,
        )
        deleted.append(resource["providerId"])

    ownership_tags = sorted({item["ownershipTag"] for item in lease["resources"]})
    residual: list[dict] = []
    for attempt in range(1, zero_verify_attempts + 1):
        residual = [
            item
            for tag in ownership_tags
            for item in _provider_call(
                lambda tag=tag: provider.list_owned_resources(tag),
                attempts=provider_attempts,
                delay=retry_delay,
                sleep=sleep,
            )
        ]
        if not residual:
            break
        if attempt < zero_verify_attempts:
            sleep(retry_delay)
    if residual:
        raise TeardownConflict("zero-resource verification found residual owned resources")
    store.transition(lease_id, "destroyed")
    return {"leaseId": lease_id, "state": "destroyed", "deletedProviderIds": deleted}


def teardown_lease_with_evidence(
    store: LeaseStore,
    provider: Provider,
    lease_id: str,
    *,
    evidence_store: EvidenceStore,
    evidence: dict[str, Any],
    actual_minor_units: int,
    clock,
    sleep=time.sleep,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run = EvidenceRun(evidence_store, evidence, clock=clock)
    result = run.execute(
        "teardown",
        lambda: teardown_lease(store, provider, lease_id, sleep=sleep),
        failure_code="teardown_failed",
        retryable=True,
    )
    return result, run.complete(actual_minor_units=actual_minor_units)


class DigitalOceanProvider:
    def __init__(self, client: Client) -> None:
        self.client = client

    @staticmethod
    def _supported(provider: str, kind: str) -> None:
        if (provider, kind) != ("digitalocean", "droplet"):
            raise TeardownConflict("resource provider/kind is not allowlisted")

    def get_resource(self, provider: str, kind: str, provider_id: str) -> dict | None:
        self._supported(provider, kind)
        try:
            return self.client.droplets.get(int(provider_id)).get("droplet")
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            if status == 404:
                return None
            raise

    def delete_resource(self, provider: str, kind: str, provider_id: str) -> None:
        self._supported(provider, kind)
        self.client.droplets.delete(int(provider_id))

    def list_owned_resources(self, ownership_tag: str) -> list[dict]:
        return self.client.droplets.list(tag_name=ownership_tag).get("droplets", [])


def _env_path() -> Path:
    configured = os.getenv("APP_ENV_PATH") or os.getenv("ENV_PATH")
    return Path(configured) if configured else Path.cwd() / ".env"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lease-id", required=True)
    parser.add_argument("--lease-root", required=True)
    parser.add_argument("--clean-dns", action="store_true")
    args = parser.parse_args(argv)
    if args.clean_dns:
        print("DNS cleanup is disabled; use the future transactional restore path", file=sys.stderr)
        return 2
    config = load_deploy_config(_env_path())
    token = config.get("DO_API_TOKEN") or os.getenv("DO_API_TOKEN")
    if not token:
        print("DO_API_TOKEN is required", file=sys.stderr)
        return 2
    if Client is None:
        print("pydo is required for the standalone teardown CLI", file=sys.stderr)
        return 2
    result = teardown_lease(
        LeaseStore(args.lease_root), DigitalOceanProvider(Client(token=token)), args.lease_id
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
