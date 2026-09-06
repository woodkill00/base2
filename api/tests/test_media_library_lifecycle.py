from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from api.services.media_library_lifecycle import (
    ASSET_TRANSITIONS,
    AssetSnapshot,
    AssetState,
    DeliveryGrant,
    MediaLifecycleError,
    Quota,
    UploadSnapshot,
    UploadState,
    admit_quota,
    exact_dedup_identity,
    object_key,
    transition_asset,
    transition_upload,
    validate_grant,
)


ASSET_ID = UUID("11111111-1111-4111-8111-111111111111")
SESSION_ID = UUID("22222222-2222-4222-8222-222222222222")
GRANT_ID = UUID("33333333-3333-4333-8333-333333333333")
NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)
DIGEST = "a" * 64


def asset(state=AssetState.UPLOADED, **changes):
    values = dict(asset_id=ASSET_ID, site_id="base2-site", state=state, version=1)
    values.update(changes)
    return AssetSnapshot(**values)


def upload(state=UploadState.CREATED, **changes):
    values = dict(
        session_id=SESSION_ID, site_id="base2-site", actor_ref="user:owner",
        expected_bytes=10, received_bytes=0, expected_sha256=DIGEST,
        state=state, version=1, expires_at=NOW + timedelta(minutes=30),
    )
    values.update(changes)
    return UploadSnapshot(**values)


def test_object_keys_are_server_owned_content_bound_and_path_safe():
    assert object_key(
        site_id="base2-site", asset_id=ASSET_ID, object_version=2, sha256=DIGEST
    ) == f"media/base2-site/{ASSET_ID.hex}/v2/{DIGEST}.bin"
    for site in ("../escape", "UPPER", "x"):
        with pytest.raises(MediaLifecycleError):
            object_key(site_id=site, asset_id=ASSET_ID, object_version=1, sha256=DIGEST)


def test_all_asset_transitions_are_explicit_and_terminal_purge_has_none():
    assert set(ASSET_TRANSITIONS) == set(AssetState)
    assert not ASSET_TRANSITIONS[AssetState.PURGED]
    current = asset()
    for target in (
        AssetState.INSPECTING, AssetState.ACCEPTED, AssetState.PROCESSING, AssetState.READY
    ):
        current = transition_asset(current, target=target, expected_version=current.version)
    assert current.state is AssetState.READY and current.version == 5


def test_invalid_and_stale_asset_transitions_fail_without_mutation():
    original = asset()
    with pytest.raises(MediaLifecycleError, match="media_transition_invalid"):
        transition_asset(original, target=AssetState.READY, expected_version=1)
    with pytest.raises(MediaLifecycleError, match="media_version_conflict"):
        transition_asset(original, target=AssetState.INSPECTING, expected_version=2)
    assert original == asset()


@pytest.mark.parametrize("held,referenced", [(True, False), (False, True), (True, True)])
def test_purge_plan_and_purge_are_blocked_by_holds_or_references(held, referenced):
    original = asset(
        AssetState.SOFT_DELETED,
        has_retention_hold=held,
        has_blocking_reference=referenced,
    )
    with pytest.raises(MediaLifecycleError, match="media_purge_blocked"):
        transition_asset(original, target=AssetState.PURGE_PLANNED, expected_version=1)


def test_upload_requires_exact_length_current_version_and_unexpired_time():
    receiving = upload(UploadState.RECEIVING, received_bytes=10)
    uploaded = transition_upload(
        receiving, target=UploadState.UPLOADED, expected_version=1, observed_at=NOW
    )
    completed = transition_upload(
        uploaded, target=UploadState.COMPLETED, expected_version=2, observed_at=NOW
    )
    assert completed.state is UploadState.COMPLETED
    with pytest.raises(MediaLifecycleError, match="media_upload_length_mismatch"):
        transition_upload(
            upload(UploadState.RECEIVING, received_bytes=9),
            target=UploadState.UPLOADED, expected_version=1, observed_at=NOW,
        )
    with pytest.raises(MediaLifecycleError, match="media_version_conflict"):
        transition_upload(
            receiving, target=UploadState.UPLOADED, expected_version=2, observed_at=NOW,
        )
    with pytest.raises(MediaLifecycleError, match="media_upload_expired"):
        transition_upload(
            receiving, target=UploadState.UPLOADED, expected_version=1,
            observed_at=NOW + timedelta(hours=1),
        )


def test_expired_upload_can_only_move_to_explicit_expired_state():
    expired = transition_upload(
        upload(), target=UploadState.EXPIRED, expected_version=1,
        observed_at=NOW + timedelta(hours=1),
    )
    assert expired.state is UploadState.EXPIRED


def test_quota_enforces_each_independent_boundary():
    quota = Quota(3, 30, 15, 100, 5)
    assert admit_quota(
        sizes=[10, 15], stored_bytes=50, active_processing_jobs=1, quota=quota
    ) == (2, 25)
    cases = [
        ([1, 1, 1, 1], 0, 0, "files"),
        ([16], 0, 0, "object"),
        ([15, 15, 1], 0, 0, "batch"),
        ([10], 95, 0, "storage"),
        ([1, 1], 0, 4, "processing"),
    ]
    for sizes, stored, active, code in cases:
        with pytest.raises(MediaLifecycleError, match=f"media_quota_{code}_exceeded"):
            admit_quota(
                sizes=sizes, stored_bytes=stored,
                active_processing_jobs=active, quota=quota,
            )


@pytest.mark.parametrize("sizes", [[], [0], [-1], [True]])
def test_quota_rejects_empty_or_nonnumeric_work(sizes):
    with pytest.raises(MediaLifecycleError):
        admit_quota(
            sizes=sizes, stored_bytes=0, active_processing_jobs=0,
            quota=Quota(3, 30, 15, 100, 5),
        )


def grant(**changes):
    values = dict(
        grant_id=GRANT_ID, site_id="base2-site", asset_id=ASSET_ID,
        object_version=3, method="GET", audience_ref="user:owner",
        issued_at=NOW, expires_at=NOW + timedelta(minutes=5), authorization_epoch=7,
    )
    values.update(changes)
    return DeliveryGrant(**values)


def validate(value, **changes):
    expected = dict(
        observed_at=NOW + timedelta(minutes=1), site_id="base2-site",
        asset_id=ASSET_ID, object_version=3, method="GET",
        audience_ref="user:owner", authorization_epoch=7,
    )
    expected.update(changes)
    validate_grant(value, **expected)


def test_delivery_grant_is_short_lived_and_exactly_scoped():
    validate(grant())
    for change in (
        {"site_id": "other-site"}, {"asset_id": SESSION_ID}, {"object_version": 4},
        {"method": "HEAD"}, {"audience_ref": "user:other"}, {"authorization_epoch": 8},
    ):
        with pytest.raises(MediaLifecycleError, match="media_grant_scope_invalid"):
            validate(grant(), **change)
    with pytest.raises(MediaLifecycleError, match="media_grant_expired"):
        validate(grant(), observed_at=NOW + timedelta(minutes=6))
    with pytest.raises(MediaLifecycleError, match="media_grant_lifetime_invalid"):
        validate(grant(expires_at=NOW + timedelta(minutes=16)))
    with pytest.raises(MediaLifecycleError, match="media_grant_method_invalid"):
        validate(grant(method="POST"), method="POST")


def test_exact_dedup_identity_is_site_scoped_without_disclosing_raw_digest():
    first = exact_dedup_identity(site_id="base2-site", sha256=DIGEST)
    second = exact_dedup_identity(site_id="other-site", sha256=DIGEST)
    assert first != second and first != DIGEST and len(first) == 64
