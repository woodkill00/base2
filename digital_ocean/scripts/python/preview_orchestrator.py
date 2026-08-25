#!/usr/bin/env python3
"""Provider-neutral, lease-bound preview deployment lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

try:
    from digital_ocean.scripts.python.deployment_evidence import EvidenceRun, EvidenceStore
    from digital_ocean.scripts.python.dns_transaction import (
        apply_dns_transaction,
        restore_dns_transaction,
    )
    from digital_ocean.scripts.python.orchestrate_teardown import teardown_lease
    from digital_ocean.scripts.python.preview_lease import LeaseStore, ownership_tag
    from digital_ocean.scripts.python.provider_admission import (
        AdmissionSnapshot,
        ProviderAdmissionController,
    )
except ModuleNotFoundError:
    from deployment_evidence import EvidenceRun, EvidenceStore
    from dns_transaction import apply_dns_transaction, restore_dns_transaction
    from orchestrate_teardown import teardown_lease
    from preview_lease import LeaseStore, ownership_tag
    from provider_admission import AdmissionSnapshot, ProviderAdmissionController


class PreviewProvider(Protocol):
    def provision(self, ownership_tag: str) -> dict[str, Any]: ...
    def dns_values(self, provider_id: str) -> list[str]: ...
    def bootstrap(self, provider_id: str) -> None: ...
    def health(self, provider_id: str) -> bool: ...
    def read_values(self, zone: str, name: str, record_type: str) -> list[str]: ...
    def replace_values(self, zone: str, name: str, record_type: str, values: list[str]) -> None: ...
    def get_resource(self, provider: str, kind: str, provider_id: str) -> dict | None: ...
    def delete_resource(self, provider: str, kind: str, provider_id: str) -> None: ...
    def list_owned_resources(self, ownership_tag: str) -> list[dict]: ...


class PreviewOrchestrationError(RuntimeError):
    pass


def _mutation_sans(lease: dict) -> set[str]:
    return {
        item["zone"] if item["name"] in {"", "@"} else f"{item['name']}.{item['zone']}"
        for item in lease["dnsMutations"]
    }


class PreviewOrchestrator:
    def __init__(
        self,
        lease_store: LeaseStore,
        evidence_store: EvidenceStore,
        provider: PreviewProvider,
        admission: ProviderAdmissionController,
        admission_snapshot: Callable[[], AdmissionSnapshot],
        *,
        clock=lambda: datetime.now(UTC),
        sleep=lambda _delay: None,
    ) -> None:
        self.leases = lease_store
        self.evidence = evidence_store
        self.provider = provider
        self.admission = admission
        self.admission_snapshot = admission_snapshot
        self.clock = clock
        self.sleep = sleep

    def _resource(self, lease: dict) -> dict:
        if len(lease["resources"]) != 1:
            raise PreviewOrchestrationError("preview lease must bind exactly one resource")
        return lease["resources"][0]

    def _rollback(self, lease_id: str) -> None:
        restore_dns_transaction(self.leases, self.provider, lease_id)
        teardown_lease(
            self.leases,
            self.provider,
            lease_id,
            retry_delay=0,
            sleep=self.sleep,
        )

    def deploy(
        self,
        lease_payload: dict,
        evidence_payload: dict,
        *,
        certificate_sans: set[str],
        actual_minor_units: int = 0,
    ) -> tuple[dict, dict]:
        lease_id = lease_payload["leaseId"]
        prior_evidence = (
            self.evidence.load(evidence_payload["runId"])
            if self.evidence.exists(evidence_payload["runId"])
            else None
        )
        if prior_evidence is not None:
            lease = self.leases.load(lease_id)
            if prior_evidence["status"] == "passed" and lease["state"] in {
                "healthy",
                "observing",
            }:
                return lease, prior_evidence

        lease = (
            self.leases.load(lease_id)
            if self.leases.exists(lease_id)
            else self.leases.create(lease_payload)
        )
        run = EvidenceRun(self.evidence, evidence_payload, clock=self.clock)
        try:
            run.execute(
                "admission",
                lambda: self._provider_operation("preview-admission", lambda: None),
                failure_code="admission_failed",
            )
            if not lease["resources"]:
                if lease["state"] == "planned":
                    lease = self.leases.transition(lease_id, "provisioning")
                tag = ownership_tag(lease_id, lease["siteId"], lease["manifestDigest"])
                remote = run.execute(
                    "provision",
                    lambda: self._provider_operation(
                        "preview-create", lambda: self._provision_owned(tag)
                    ),
                    failure_code="provision_failed",
                    retryable=True,
                )
                resource = {
                    "provider": "digitalocean",
                    "kind": "droplet",
                    "providerId": str(remote.get("id", "")),
                    "ownershipTag": tag,
                }
                lease = self.leases.add_resource(lease_id, resource)
            resource = self._resource(lease)
            desired_sets = [item["desiredValues"] for item in lease["dnsMutations"]]
            if desired_sets and not any(desired_sets):
                desired_values = run.execute(
                    "dns-bind",
                    lambda: self._provider_operation(
                        "preview-dns-bind",
                        lambda: self.provider.dns_values(resource["providerId"]),
                    ),
                    failure_code="dns_bind_failed",
                    retryable=True,
                )
                lease = self.leases.bind_dns_desired_values(lease_id, desired_values)
            elif desired_sets and not all(desired_sets):
                raise PreviewOrchestrationError("DNS desired-value state is inconsistent")
            if lease["state"] == "provisioning":
                lease = self.leases.transition(lease_id, "bootstrapping")
            run.execute(
                "bootstrap",
                lambda: self._provider_operation(
                    "preview-bootstrap",
                    lambda: self.provider.bootstrap(resource["providerId"]),
                ),
                failure_code="bootstrap_failed",
                retryable=True,
            )

            lease = self.leases.load(lease_id)
            sans = _mutation_sans(lease)
            if lease["dnsMutations"]:
                run.execute(
                    "dns",
                    lambda: self._provider_operation(
                        "preview-dns",
                        lambda: apply_dns_transaction(
                            self.leases,
                            self.provider,
                            lease_id,
                            health_check=lambda: self.provider.health(resource["providerId"]),
                            required_sans=sans,
                            certificate_sans=certificate_sans,
                        ),
                    ),
                    failure_code="dns_failed",
                )
            else:
                run.execute("dns", lambda: None, failure_code="dns_failed")
            run.execute(
                "health",
                lambda: self._provider_operation(
                    "preview-health",
                    lambda: self._require_health(resource["providerId"]),
                ),
                failure_code="health_failed",
                retryable=True,
            )
            lease = self.leases.load(lease_id)
            if lease["state"] == "bootstrapping":
                lease = self.leases.transition(lease_id, "healthy")
            return lease, run.complete(actual_minor_units=actual_minor_units)
        except Exception:
            self._rollback(lease_id)
            raise

    def update(
        self,
        lease_id: str,
        evidence_payload: dict,
        *,
        actual_minor_units: int = 0,
    ) -> tuple[dict, dict]:
        lease = self.leases.load(lease_id)
        resource = self._resource(lease)
        run = EvidenceRun(self.evidence, evidence_payload, clock=self.clock)
        run.execute(
            "bootstrap",
            lambda: self._provider_operation(
                "preview-update", lambda: self.provider.bootstrap(resource["providerId"])
            ),
            failure_code="update_failed",
            retryable=True,
        )
        run.execute(
            "health",
            lambda: self._provider_operation(
                "preview-health", lambda: self._require_health(resource["providerId"])
            ),
            failure_code="health_failed",
            retryable=True,
        )
        return lease, run.complete(actual_minor_units=actual_minor_units)

    def rollback(
        self,
        lease_id: str,
        evidence_payload: dict,
        *,
        actual_minor_units: int = 0,
    ) -> tuple[dict, dict]:
        run = EvidenceRun(self.evidence, evidence_payload, clock=self.clock)
        run.execute(
            "teardown",
            lambda: self._rollback(lease_id),
            failure_code="rollback_failed",
            retryable=True,
        )
        return self.leases.load(lease_id), run.complete(actual_minor_units=actual_minor_units)

    def _require_health(self, provider_id: str) -> None:
        if self.provider.health(provider_id) is not True:
            raise PreviewOrchestrationError("preview health gate failed")

    def _provider_operation(self, scope: str, operation: Callable[[], Any]) -> Any:
        return self.admission.execute(scope, self.admission_snapshot(), operation)

    def _provision_owned(self, tag: str) -> dict[str, Any]:
        remote = self.provider.provision(tag)
        if not str(remote.get("id", "")) or tag not in remote.get("tags", []):
            raise PreviewOrchestrationError("provisioned resource lacks exact ownership")
        return remote
