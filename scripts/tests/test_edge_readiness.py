import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.python.edge_readiness import (
    EdgeReadinessError,
    cache_headers,
    canonical_redirect,
    domain_claim,
    private_surface_access,
    validate_edge_policy,
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
    assert "immutable" in cache_headers("public-static")["Cache-Control"]


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
