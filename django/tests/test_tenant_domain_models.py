from datetime import UTC, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError

from sitecontent.models import TenantDomainClaim

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def claim(**changed):
    values = {
        "site_id": "tenant-one",
        "domain": "Example.COM.",
        "challenge_digest": "a" * 64,
        "state": "pending",
        "expires_at": NOW + timedelta(minutes=15),
    }
    values.update(changed)
    return TenantDomainClaim(**values)


def test_claim_normalizes_and_validates_closed_domain():
    value = claim()
    value.full_clean(validate_unique=False, validate_constraints=False)
    assert value.domain == "example.com"
    for hostile in ("*.example.com", "xn--pple-43d.com", "localhost", "example.com/path"):
        with pytest.raises(ValidationError):
            claim(domain=hostile).full_clean(validate_unique=False, validate_constraints=False)


def test_verified_and_active_states_require_exact_evidence_and_release_binding():
    verified = claim(state="verified", verified_at=NOW, evidence_digest="b" * 64)
    verified.full_clean(validate_unique=False, validate_constraints=False)
    active = claim(
        state="active", canonical=True, verified_at=NOW, evidence_digest="b" * 64,
        approval_digest="c" * 64, release_id="release-001",
    )
    active.full_clean(validate_unique=False, validate_constraints=False)
    with pytest.raises(ValidationError, match="activation_binding"):
        claim(
            state="active", verified_at=NOW, evidence_digest="b" * 64
        ).full_clean(validate_unique=False, validate_constraints=False)
    with pytest.raises(ValidationError, match="canonical_state"):
        claim(canonical=True).full_clean(validate_unique=False, validate_constraints=False)
