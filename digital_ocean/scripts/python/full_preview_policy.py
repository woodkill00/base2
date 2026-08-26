#!/usr/bin/env python3
"""Strict policy for the guarded, staging-only Base2 full preview."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from pathlib import Path


DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
MODES = {
    "local": Path("dynamic.yml"),
    "minimal-canary": Path("dynamic-canary.yml"),
    "full-preview": Path("dynamic-full-preview.yml"),
}


class PolicyError(ValueError):
    """Preview policy is unsafe or ambiguous."""


def validate_owner_cidrs(values: list[str]) -> tuple[str, ...]:
    if not isinstance(values, list) or not 1 <= len(values) <= 4:
        raise PolicyError("owner CIDRs require one to at most four entries")
    normalized: list[str] = []
    for raw in values:
        try:
            network = ipaddress.ip_network(str(raw), strict=True)
        except ValueError as exc:
            raise PolicyError("owner CIDR is invalid") from exc
        exact_prefix = 32 if network.version == 4 else 128
        if network.prefixlen != exact_prefix:
            raise PolicyError("owner CIDR must identify one exact host")
        address = network.network_address
        if (
            not address.is_global
            or address.is_multicast
            or address.is_unspecified
            or address.is_loopback
            or address.is_link_local
            or address.is_private
            or address.is_reserved
        ):
            raise PolicyError("owner CIDR must be a globally routable address")
        normalized.append(str(network))
    if len(set(normalized)) != len(normalized):
        raise PolicyError("owner CIDR is duplicated")
    return tuple(normalized)


def select_dynamic_template(mode: str) -> Path:
    try:
        return MODES[mode]
    except KeyError as exc:
        raise PolicyError("preview routing mode is not allowlisted") from exc


def _route(host: str, path: str, service: str, exposure: str) -> dict:
    protected = exposure == "protected-edge"
    return {
        "host": host,
        "path": path,
        "service": service,
        "exposure": exposure,
        "edgeAuth": protected,
        "ownerAllowlist": protected,
    }


def full_preview_policy(domain: str, owner_cidrs: list[str], *, ttl_minutes: int = 60) -> dict:
    domain = str(domain).strip().lower()
    if not DOMAIN.fullmatch(domain):
        raise PolicyError("canonical preview domain is invalid")
    if not isinstance(ttl_minutes, int) or isinstance(ttl_minutes, bool) or not 15 <= ttl_minutes <= 240:
        raise PolicyError("preview TTL must be between 15 and 240 minutes")
    cidrs = validate_owner_cidrs(owner_cidrs)
    routes = [
        _route(domain, "/", "frontend", "public"),
        _route(domain, "/api", "api-index", "public"),
        _route(domain, "/api/health", "api-health", "public"),
        _route(f"admin.{domain}", "/admin/", "django-admin", "protected-edge"),
        _route(f"swagger.{domain}", "/docs", "swagger", "protected-edge"),
        _route(f"traefik.{domain}", "/", "traefik", "protected-edge"),
        _route(f"pgadmin.{domain}", "/", "pgadmin", "protected-edge"),
        _route(f"flower.{domain}", "/", "flower", "protected-edge"),
    ]
    return {
        "schemaVersion": 1,
        "mode": "full-preview",
        "profileId": "base2-obsidian",
        "certificateMode": "letsencrypt-staging-only",
        "ownerCidrs": list(cidrs),
        "ownerAdmissionDigest": hashlib.sha256(",".join(cidrs).encode()).hexdigest(),
        "ttlMinutes": ttl_minutes,
        "routes": routes,
    }


def safe_receipt(policy: dict) -> dict:
    return {
        "schemaVersion": policy["schemaVersion"],
        "mode": policy["mode"],
        "profileId": policy["profileId"],
        "certificateMode": policy["certificateMode"],
        "ownerAdmissionDigest": policy["ownerAdmissionDigest"],
        "ownerCidrCount": len(policy["ownerCidrs"]),
        "routeCount": len(policy["routes"]),
        "rawValuesReturned": False,
    }


def canonical_digest(policy: dict) -> str:
    return hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
