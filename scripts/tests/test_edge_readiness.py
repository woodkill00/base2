import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.python.edge_readiness import (
    EdgeReadinessError,
    cache_headers,
    canonical_redirect,
    certificate_transition,
    domain_claim,
    domain_verification_evidence,
    private_surface_access,
    transition_domain_claim,
    validate_edge_policy,
    validate_resolved_origin,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def test_edge_policy_is_closed_staging_only_and_default_deny():
    policy = json.loads((ROOT / "shared/config/edge-readiness-v1.json").read_text())
    assert validate_edge_policy(policy)["network"]["egressDefault"] == "deny"
    changed = json.loads(json.dumps(policy))
    changed["certificateModes"]["preview"] = "production"
    with pytest.raises(EdgeReadinessError, match="certificate"):
        validate_edge_policy(changed)


def test_domain_claim_is_tenant_expiry_and_challenge_bound():
    claim = domain_claim(
        tenant_id="tenant-one",
        domain="Example.COM.",
        challenge_digest="a" * 64,
        expires_at=NOW + timedelta(minutes=15),
    )
    assert claim["domain"] == "example.com"
    assert len(claim["claimDigest"]) == 64
    for domain in ("*.example.com", "xn--pple-43d.com", "other.xn--pple-43d.com"):
        with pytest.raises(EdgeReadinessError, match="claim_invalid"):
            domain_claim(
                tenant_id="tenant-one",
                domain=domain,
                challenge_digest="a" * 64,
                expires_at=NOW + timedelta(minutes=15),
            )


def test_canonical_https_redirect_is_deterministic_and_rejects_host_confusion():
    assert canonical_redirect(request_host="www.example.com", apex="example.com", https=False) == {
        "redirect": True,
        "status": 308,
        "canonicalOrigin": "https://example.com",
    }
    assert (
        canonical_redirect(request_host="example.com", apex="example.com", https=True)["redirect"]
        is False
    )
    with pytest.raises(EdgeReadinessError, match="host_unowned"):
        canonical_redirect(request_host="attacker.test", apex="example.com", https=True)


def test_private_and_signed_responses_never_enter_shared_cache():
    for classification in ("authenticated", "tenant-private", "signed"):
        assert cache_headers(classification) == {
            "Cache-Control": "private,no-store",
            "Vary": "Cookie,Authorization",
        }
    public = cache_headers("public-static", version_digest="a" * 64)
    assert "immutable" in public["Cache-Control"]
    assert public["ETag"] == '"sha256-' + "a" * 64 + '"'
    with pytest.raises(EdgeReadinessError, match="cache_version"):
        cache_headers("public-media")


def test_private_surfaces_require_role_recent_auth_and_private_network():
    assert private_surface_access(
        surface="pgadmin",
        authenticated=True,
        role="operator",
        network="private-overlay",
        recent_auth=True,
    )
    for changed in (
        {"authenticated": False},
        {"role": "member"},
        {"network": "public"},
        {"recent_auth": False},
    ):
        context = {
            "surface": "pgadmin",
            "authenticated": True,
            "role": "operator",
            "network": "private-overlay",
            "recent_auth": True,
            **changed,
        }
        assert private_surface_access(**context) is False


def test_domain_lifecycle_requires_exact_release_approval_and_replays():
    key = b"k" * 32
    verification_key = b"v" * 32
    claim = domain_claim(
        tenant_id="tenant-one", domain="example.com", challenge_digest="a" * 64,
        expires_at=NOW + timedelta(minutes=15),
    )
    evidence = domain_verification_evidence(
        claim=claim,
        observed_challenge_digest='a' * 64,
        observed_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        key=verification_key,
    )
    verified = transition_domain_claim(
        claim, action="verify", now=NOW, verification_evidence=evidence,
        verification_key=verification_key,
    )
    message = f'{claim["claimDigest"]}:activate:release-001'.encode()
    approval = hmac.new(key, message, hashlib.sha256).hexdigest()
    active = transition_domain_claim(
        verified, action="activate", now=NOW, release_id="release-001",
        approval=approval, approval_key=key,
    )
    assert active["state"] == "active" and active["canonical"] is True
    assert transition_domain_claim(
        active, action="activate", now=NOW, release_id="release-001",
        approval=approval, approval_key=key,
    ) == active
    with pytest.raises(EdgeReadinessError, match="approval"):
        transition_domain_claim(
            verified, action="activate", now=NOW, release_id="release-002",
            approval=approval, approval_key=key,
        )
    changed = dict(evidence)
    changed['domain'] = 'attacker.example'
    with pytest.raises(EdgeReadinessError, match='verification'):
        transition_domain_claim(
            claim, action='verify', now=NOW, verification_evidence=changed,
            verification_key=verification_key,
        )


def test_expired_claim_fails_closed_and_staging_cert_lifecycle_is_bounded():
    claim = domain_claim(
        tenant_id="tenant-one", domain="example.com", challenge_digest="a" * 64,
        expires_at=NOW + timedelta(minutes=1),
    )
    expired = transition_domain_claim(
        claim, action="verify", now=NOW + timedelta(minutes=2)
    )
    assert expired["state"] == "expired"
    assert certificate_transition(
        environment="preview", state="absent", action="request", now=NOW
    )["endpoint"] == "acme-staging"
    with pytest.raises(EdgeReadinessError, match="issuance_disabled"):
        certificate_transition(environment="test", state="absent", action="request", now=NOW)
    with pytest.raises(EdgeReadinessError, match="production_approval"):
        certificate_transition(
            environment="production", state="absent", action="request", now=NOW
        )


def test_origin_resolution_rejects_ssrf_metadata_private_and_rebinding_targets():
    assert validate_resolved_origin(
        hostname="objects.example.net", addresses=["93.184.216.34"],
        allowed_hosts={"objects.example.net"},
    )
    for host, addresses in (
        ("metadata.internal", ["169.254.169.254"]),
        ("objects.example.net", ["127.0.0.1"]),
        ("objects.example.net", ["10.0.0.3"]),
        ("objects.example.net", ["fe80::1"]),
    ):
        with pytest.raises(EdgeReadinessError, match="egress_denied"):
            validate_resolved_origin(
                hostname=host, addresses=addresses, allowed_hosts={"objects.example.net"}
            )
