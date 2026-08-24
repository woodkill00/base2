#!/usr/bin/env python3
"""Exact-before-state DNS transaction for preview leases."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

try:
    from digital_ocean.scripts.python.deployment_evidence import EvidenceRun, EvidenceStore
    from digital_ocean.scripts.python.preview_lease import LeaseStore
except ModuleNotFoundError:
    from deployment_evidence import EvidenceRun, EvidenceStore
    from preview_lease import LeaseStore


class DnsConflict(RuntimeError):
    """DNS state or health evidence does not match the reviewed transaction."""


class DnsProvider(Protocol):
    def read_values(self, zone: str, name: str, record_type: str) -> list[str]: ...
    def replace_values(self, zone: str, name: str, record_type: str, values: list[str]) -> None: ...


def _current(provider: DnsProvider, mutation: dict) -> list[str]:
    return sorted(provider.read_values(mutation["zone"], mutation["name"], mutation["type"]))


def _replace(provider: DnsProvider, mutation: dict, values: list[str]) -> None:
    provider.replace_values(mutation["zone"], mutation["name"], mutation["type"], values)


def apply_dns_transaction(
    store: LeaseStore,
    provider: DnsProvider,
    lease_id: str,
    *,
    health_check: Callable[[], bool],
    required_sans: set[str],
    certificate_sans: set[str],
) -> dict:
    if required_sans != certificate_sans:
        raise DnsConflict("certificate SAN set does not exactly match required names")
    lease = store.load(lease_id)
    mutations = lease["dnsMutations"]
    if not mutations:
        raise DnsConflict("lease has no DNS transaction receipt")
    mutation_sans = {
        mutation["zone"]
        if mutation["name"] in {"", "@"}
        else f"{mutation['name']}.{mutation['zone']}"
        for mutation in mutations
    }
    if mutation_sans != required_sans:
        raise DnsConflict("DNS mutation names do not exactly match required SAN set")

    # Preflight every record before the first mutation. A planned record that
    # already has desired values is an interrupted apply and can be reconciled.
    for mutation in mutations:
        if mutation["state"] in {"verified", "restored"}:
            continue
        current = _current(provider, mutation)
        previous = sorted(mutation["previousValues"])
        desired = sorted(mutation["desiredValues"])
        if current not in (previous, desired):
            raise DnsConflict("stale DNS state differs from exact prior and desired values")

    for index, mutation in enumerate(mutations):
        if mutation["state"] in {"verified", "restored"}:
            continue
        if _current(provider, mutation) == sorted(mutation["previousValues"]):
            _replace(provider, mutation, mutation["desiredValues"])
        lease = store.update_dns_state(lease_id, index, "applied")
        mutations = lease["dnsMutations"]

    healthy = False
    try:
        healthy = health_check() is True
    except Exception:
        healthy = False
    if healthy:
        for index, mutation in enumerate(store.load(lease_id)["dnsMutations"]):
            if mutation["state"] == "applied":
                store.update_dns_state(lease_id, index, "verified")
        return store.load(lease_id)

    # Roll back only exact desired values, in reverse order. Any third-party
    # change blocks restoration rather than overwriting it.
    for index in reversed(range(len(mutations))):
        mutation = store.load(lease_id)["dnsMutations"][index]
        if mutation["state"] != "applied":
            continue
        current = _current(provider, mutation)
        desired = sorted(mutation["desiredValues"])
        previous = sorted(mutation["previousValues"])
        if current == desired:
            _replace(provider, mutation, mutation["previousValues"])
        elif current != previous:
            raise DnsConflict("DNS changed during rollback; exact restoration refused")
        store.update_dns_state(lease_id, index, "restored")
    raise DnsConflict("health gate failed; exact prior DNS values restored")


def restore_dns_transaction(
    store: LeaseStore,
    provider: DnsProvider,
    lease_id: str,
) -> dict:
    """Restore every lease-owned DNS mutation without overwriting drift."""
    lease = store.load(lease_id)
    for index in reversed(range(len(lease["dnsMutations"]))):
        mutation = store.load(lease_id)["dnsMutations"][index]
        if mutation["state"] == "restored":
            continue
        current = _current(provider, mutation)
        desired = sorted(mutation["desiredValues"])
        previous = sorted(mutation["previousValues"])
        if current == desired:
            _replace(provider, mutation, mutation["previousValues"])
        elif current != previous:
            raise DnsConflict("DNS changed before teardown; exact restoration refused")
        store.update_dns_state(lease_id, index, "restored")
    return store.load(lease_id)


def apply_dns_with_evidence(
    store: LeaseStore,
    provider: DnsProvider,
    lease_id: str,
    *,
    health_check: Callable[[], bool],
    required_sans: set[str],
    certificate_sans: set[str],
    evidence_store: EvidenceStore,
    evidence: dict,
    actual_minor_units: int,
    clock,
) -> tuple[dict, dict]:
    run = EvidenceRun(evidence_store, evidence, clock=clock)
    result = run.execute(
        "dns",
        lambda: apply_dns_transaction(
            store,
            provider,
            lease_id,
            health_check=health_check,
            required_sans=required_sans,
            certificate_sans=certificate_sans,
        ),
        failure_code="dns_transaction_failed",
        retryable=False,
    )
    return result, run.complete(actual_minor_units=actual_minor_units)
