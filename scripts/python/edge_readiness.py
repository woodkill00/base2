#!/usr/bin/env python3
"""Closed domain, certificate, cache, private-surface, and edge contracts."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import re
from datetime import UTC, datetime, timedelta
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


def transition_domain_claim(
    claim: dict[str, Any],
    *,
    action: str,
    now: datetime,
    evidence_digest: str = "",
    release_id: str = "",
    approval: str = "",
    approval_key: bytes | None = None,
) -> dict[str, Any]:
    """Advance a claim without network access or caller-selected commands/URLs."""
    value = json.loads(json.dumps(claim, sort_keys=True))
    if now.tzinfo is None or value.get("state") not in {
        "pending", "verified", "active", "revoked", "expired"
    }:
        raise EdgeReadinessError("domain:state_invalid")
    expires = datetime.fromisoformat(value["expiresAt"])
    if now.astimezone(UTC) >= expires and value["state"] not in {"revoked", "expired"}:
        value.update(state="expired", canonical=False)
        return value
    if action == "verify":
        if value["state"] == "verified" and value.get("evidenceDigest") == evidence_digest:
            return value
        if value["state"] != "pending" or not re.fullmatch(r"[0-9a-f]{64}", evidence_digest):
            raise EdgeReadinessError("domain:verification_invalid")
        value.update(state="verified", evidenceDigest=evidence_digest, verifiedAt=now.isoformat())
        return value
    if action in {"activate", "revoke"}:
        if not approval_key or len(approval_key) < 32 or not re.fullmatch(
            r"[a-z0-9][a-z0-9_.-]{2,127}", release_id or ""
        ):
            raise EdgeReadinessError("domain:approval_invalid")
        message = f'{value["claimDigest"]}:{action}:{release_id}'.encode()
        expected = hmac.new(approval_key, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, approval):
            raise EdgeReadinessError("domain:approval_invalid")
        target = "active" if action == "activate" else "revoked"
        allowed = {"activate": {"verified", "active"}, "revoke": {"verified", "active", "revoked"}}
        if value["state"] not in allowed[action]:
            raise EdgeReadinessError("domain:transition_invalid")
        if value["state"] == target and value.get("releaseId") == release_id:
            return value
        value.update(
            state=target,
            canonical=action == "activate",
            releaseId=release_id,
            approvalDigest=hashlib.sha256(approval.encode()).hexdigest(),
        )
        return value
    raise EdgeReadinessError("domain:action_invalid")


def canonical_redirect(*, request_host: str, apex: str, https: bool) -> dict[str, Any]:
    request = request_host.lower().rstrip(".")
    target = apex.lower().rstrip(".")
    if not DOMAIN.fullmatch(request) or not DOMAIN.fullmatch(target):
        raise EdgeReadinessError("domain:host_invalid")
    canonical = f"https://{target}"
    if request not in {target, f"www.{target}"}:
        raise EdgeReadinessError("domain:host_unowned")
    return {"redirect": request != target or not https, "status": 308, "canonicalOrigin": canonical}


def cache_headers(classification: str, *, version_digest: str = "") -> dict[str, str]:
    if classification not in CACHE:
        raise EdgeReadinessError("edge:cache_class_invalid")
    if classification in {"public-static", "public-media"}:
        if not re.fullmatch(r"[0-9a-f]{64}", version_digest or ""):
            raise EdgeReadinessError("edge:cache_version_invalid")
        policy = (
            "public,max-age=31536000,immutable"
            if classification == "public-static"
            else "public,max-age=3600,must-revalidate"
        )
        return {
            "Cache-Control": policy,
            "Vary": "Accept-Encoding",
            "ETag": f'"sha256-{version_digest}"',
        }
    return {"Cache-Control": "private,no-store", "Vary": "Cookie,Authorization"}


def certificate_transition(
    *, environment: str, state: str, action: str, now: datetime, expires_at: datetime | None = None
) -> dict[str, Any]:
    modes = {
        "development": "disabled",
        "test": "disabled",
        "preview": "staging-only",
        "staging": "staging-only",
        "production": "separate-approval",
    }
    if environment not in modes or now.tzinfo is None:
        raise EdgeReadinessError("certificate:environment_invalid")
    if environment in {"development", "test"}:
        raise EdgeReadinessError("certificate:issuance_disabled")
    if environment == "production":
        raise EdgeReadinessError("certificate:production_approval_required")
    transitions = {
        ("absent", "request"): "pending",
        ("pending", "issue"): "active",
        ("active", "renew"): "pending",
        ("active", "revoke"): "revoked",
        ("pending", "fail"): "failed",
        ("failed", "retry"): "pending",
    }
    target = transitions.get((state, action))
    if not target:
        raise EdgeReadinessError("certificate:transition_invalid")
    if target == "active" and (expires_at is None or expires_at <= now + timedelta(hours=1)):
        raise EdgeReadinessError("certificate:expiry_invalid")
    return {"environment": environment, "endpoint": "acme-staging", "state": target}


def validate_resolved_origin(*, hostname: str, addresses: list[str], allowed_hosts: set[str]) -> bool:
    """Reject unapproved names, rebinding, metadata, loopback, and private origins."""
    host = hostname.lower().rstrip(".")
    if host not in allowed_hosts or not addresses:
        raise EdgeReadinessError("edge:egress_denied")
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if not address.is_global:
            raise EdgeReadinessError("edge:egress_denied")
    return True


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
