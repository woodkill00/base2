from datetime import UTC, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError

from sitecontent.models import BreakGlassGrant, DurableJob, DurableSchedule

NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def test_durable_job_enforces_lease_and_result_invariants():
    value = DurableJob(
        site_id="tenant-one", owner_ref="owner", job_type="search.reindex",
        payload_digest="a" * 64, idempotency_key="job.reindex-001", state="queued",
        available_at=NOW,
    )
    value.full_clean(validate_unique=False, validate_constraints=False)
    value.state = "leased"
    with pytest.raises(ValidationError, match="lease_invalid"):
        value.full_clean(validate_unique=False, validate_constraints=False)


def test_schedule_and_break_glass_validation_fail_closed():
    DurableSchedule(
        site_id="tenant-one", schedule_key="daily.search", job_type="search.reindex",
        timezone="Europe/Berlin", rule="0 3 * * *", next_run_at=NOW,
    ).full_clean(validate_unique=False, validate_constraints=False)
    with pytest.raises(ValidationError, match="timezone_invalid"):
        DurableSchedule(
            site_id="tenant-one", schedule_key="daily.search", job_type="search.reindex",
            timezone="Not/AZone", rule="0 3 * * *", next_run_at=NOW,
        ).full_clean(validate_unique=False, validate_constraints=False)
    with pytest.raises(ValidationError, match="independent_approval"):
        BreakGlassGrant(
            site_id="tenant-one", requester_ref="owner", approver_ref="owner",
            scope="operations.read", reason_digest="a" * 64, approval_digest="b" * 64,
            expires_at=NOW + timedelta(minutes=15),
        ).full_clean(validate_unique=False, validate_constraints=False)
