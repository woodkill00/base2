#!/usr/bin/env python3
"""Transactional exact-record DNS migration for a Base2 full preview."""
from __future__ import annotations
import ipaddress
import re
from typing import Any, Protocol

REQUIRED_SUBDOMAINS = ("admin", "swagger", "traefik", "pgadmin", "flower")
DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")

class DnsMigrationError(RuntimeError):
    pass

class DnsProvider(Protocol):
    def list_records(self, domain: str) -> list[dict[str, Any]]: ...
    def create_record(self, domain: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def delete_record(self, domain: str, record_id: int) -> None: ...


def required_names(domain: str) -> tuple[str, ...]:
    """Return canonical provider identities for the required records."""
    normalized = str(domain).strip().lower()
    if not DOMAIN.fullmatch(normalized):
        raise DnsMigrationError("DNS domain is invalid")
    return ("@", *REQUIRED_SUBDOMAINS)


def _request_name(domain: str, canonical_name: str) -> str:
    """Translate DigitalOcean's apex identity into its raw-API request form."""
    return f"{domain}." if canonical_name == "@" else canonical_name

def _row(payload: dict) -> dict:
    value = payload.get("domain_record", payload)
    required = ("id", "type", "name", "data")
    if not isinstance(value, dict) or any(key not in value for key in required):
        raise DnsMigrationError("provider returned malformed DNS identity")
    return {"id": str(value["id"]), "type": str(value["type"]), "name": str(value["name"]), "value": str(value["data"])}

def migrate_required_records(provider: DnsProvider, domain: str, ip_address: str, *, ttl: int = 60) -> dict:
    names = required_names(domain)
    parsed_address = ipaddress.IPv4Address(ip_address)
    if not parsed_address.is_global:
        raise DnsMigrationError("DNS target must be one public IPv4 address")
    address = str(parsed_address)
    if not 30 <= ttl <= 300:
        raise DnsMigrationError("DNS TTL exceeds preview policy")
    listed = provider.list_records(domain)
    if isinstance(listed, dict):
        listed = listed.get("domain_records")
    if not isinstance(listed, list):
        raise DnsMigrationError("provider returned malformed DNS inventory")
    inventory = [_row(row) for row in listed]
    prior_names = set(names) | {domain, f"{domain}."}
    prior = [row for row in inventory if row["type"] == "A" and row["name"] in prior_names]
    created: list[dict] = []
    deleted_prior: list[dict] = []
    try:
        for name in names:
            request_name = _request_name(domain, name)
            row = _row(provider.create_record(domain, {"type": "A", "name": request_name, "data": address, "ttl": ttl}))
            created.append(row)
            if row["type"] != "A" or row["name"] != name or row["value"] != address:
                raise DnsMigrationError("provider returned a different DNS record")
        for row in prior:
            provider.delete_record(domain, int(row["id"]))
            deleted_prior.append(row)
    except Exception as exc:
        rollback_errors = []
        for row in reversed(deleted_prior):
            try:
                provider.create_record(domain, {"type": row["type"], "name": _request_name(domain, row["name"]), "data": row["value"], "ttl": ttl})
            except Exception as rollback:
                rollback_errors.append(type(rollback).__name__)
        for row in reversed(created):
            try:
                provider.delete_record(domain, int(row["id"]))
            except Exception as rollback:
                rollback_errors.append(type(rollback).__name__)
        if rollback_errors:
            raise DnsMigrationError("DNS migration failed and rollback requires reconciliation") from exc
        raise DnsMigrationError("DNS migration failed and was rolled back") from exc
    return {
        "schemaVersion": 1, "domain": domain, "value": address,
        "records": [{"id": row["id"], "domain": domain, "type": "A", "name": row["name"], "value": address, "state": "bound"} for row in created],
        "replacedRecords": prior,
        "replacedRecordCount": len(prior), "createdRecordCount": len(created), "secretValuesEmitted": 0,
    }


def restore_migration(provider: DnsProvider, receipt: dict, *, ttl: int = 60) -> dict:
    """Remove exact created identities, then restore the prior public DNS set."""
    if receipt.get("schemaVersion") != 1 or not 30 <= ttl <= 300:
        raise DnsMigrationError("DNS rollback receipt is invalid")
    deleted = 0
    restored = 0
    try:
        for row in reversed(receipt.get("records") or []):
            provider.delete_record(row["domain"], int(row["id"]))
            deleted += 1
        for row in receipt.get("replacedRecords") or []:
            provider.create_record(
                receipt["domain"],
                {"type": row["type"], "name": _request_name(receipt["domain"], row["name"]), "data": row["value"], "ttl": ttl},
            )
            restored += 1
    except Exception as exc:
        raise DnsMigrationError("DNS rollback requires reconciliation") from exc
    return {"ok": True, "createdRecordsDeleted": deleted, "priorRecordsRestored": restored, "secretValuesEmitted": 0}
