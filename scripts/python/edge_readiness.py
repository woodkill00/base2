#!/usr/bin/env python3
"""Closed domain, certificate, cache, private-surface, and edge contracts."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import UTC, datetime
from typing import Any

DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
PRIVATE = {"django-admin", "pgadmin", "traefik", "metrics", "diagnostics", "api-schema"}
CACHE = {"public-static", "public-media", "authenticated", "tenant-private", "signed"}


class EdgeReadinessError(ValueError):
    pass


def validate_edge_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion",
        "certificateModes",
        "privateSurfaces",
        "cacheClasses",
        "limits",
        "network",
    }:
        raise EdgeReadinessError("edge:policy_invalid")
    if value["schemaVersion"] != 1 or value["certificateModes"] != {
        "development": "disabled",
        "test": "disabled",
        "preview": "staging-only",
        "staging": "staging-only",
        "production": "separate-approval",
    }:
        raise EdgeReadinessError("edge:certificate_policy_invalid")
    if set(value["privateSurfaces"]) != PRIVATE or set(value["cacheClasses"]) != CACHE:
        raise EdgeReadinessError("edge:surface_policy_invalid")
    expected_cache = {
        "public-static": "versioned-public-immutable",
        "public-media": "versioned-public-revalidate",
        "authenticated": "private-no-store",
        "tenant-private": "private-no-store",
        "signed": "private-no-store",
    }
    if value["cacheClasses"] != expected_cache:
        raise EdgeReadinessError("edge:cache_policy_invalid")
    limits = value["limits"]
    if (
        not isinstance(limits, dict)
        or set(limits)
        != {
            "bodyBytes",
            "headerBytes",
            "requestSeconds",
            "upstreamSeconds",
            "requestsPerMinute",
            "concurrentPerTenant",
        }
        or any(type(item) is not int or item < 1 for item in limits.values())
    ):
        raise EdgeReadinessError("edge:limits_invalid")
    if limits["bodyBytes"] > 16 * 1024 * 1024 or limits["headerBytes"] > 64 * 1024:
        raise EdgeReadinessError("edge:limits_invalid")
    network = value["network"]
    if network != {
        "metadataCidrsDenied": ["169.254.0.0/16", "fe80::/10"],
        "serviceDefault": "deny",
        "egressDefault": "deny",
        "dnsRebindingProtection": True,
        "encryptedOrigin": True,
    }:
        raise EdgeReadinessError("edge:network_policy_invalid")
    for item in network["metadataCidrsDenied"]:
        ipaddress.ip_network(item)
    return json.loads(json.dumps(value, sort_keys=True))


def domain_claim(
    *, tenant_id: str, domain: str, challenge_digest: str, expires_at: datetime
) -> dict[str, Any]:
    canonical = domain.strip().lower().rstrip(".")
    if (
        not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", tenant_id or "")
        or "*" in canonical
        or not DOMAIN.fullmatch(canonical)
        or canonical.startswith("xn--")
        or ".xn--" in canonical
        or not re.fullmatch(r"[0-9a-f]{64}", challenge_digest or "")
        or expires_at.tzinfo is None
    ):
        raise EdgeReadinessError("domain:claim_invalid")
    value = {
        "tenantId": tenant_id,
        "domain": canonical,
        "challengeDigest": challenge_digest,
        "expiresAt": expires_at.astimezone(UTC).isoformat(),
        "state": "pending",
    }
    value["claimDigest"] = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return value


def canonical_redirect(*, request_host: str, apex: str, https: bool) -> dict[str, Any]:
    request = request_host.lower().rstrip(".")
    target = apex.lower().rstrip(".")
    if not DOMAIN.fullmatch(request) or not DOMAIN.fullmatch(target):
        raise EdgeReadinessError("domain:host_invalid")
    canonical = f"https://{target}"
    if request not in {target, f"www.{target}"}:
        raise EdgeReadinessError("domain:host_unowned")
    return {"redirect": request != target or not https, "status": 308, "canonicalOrigin": canonical}


def cache_headers(classification: str) -> dict[str, str]:
    if classification not in CACHE:
        raise EdgeReadinessError("edge:cache_class_invalid")
    if classification == "public-static":
        return {"Cache-Control": "public,max-age=31536000,immutable", "Vary": "Accept-Encoding"}
    if classification == "public-media":
        return {"Cache-Control": "public,max-age=3600,must-revalidate", "Vary": "Accept-Encoding"}
    return {"Cache-Control": "private,no-store", "Vary": "Cookie,Authorization"}


def private_surface_access(
    *, surface: str, authenticated: bool, role: str, network: str, recent_auth: bool
) -> bool:
    if surface not in PRIVATE:
        raise EdgeReadinessError("edge:surface_invalid")
    return (
        authenticated
        and role in {"owner", "operator"}
        and network in {"loopback", "private-overlay"}
        and recent_auth
    )
