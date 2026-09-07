"""Pure lifecycle, quota, identity, and delivery contracts for media assets."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Iterable
from uuid import UUID

from api.services.media_library_policy import FORMAT_RULES, MediaPolicyError, validate_digest


SITE_ID = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
ACTOR_REF = re.compile(r"^[a-z][a-z0-9:._-]{2,199}$")


class MediaLifecycleError(ValueError):
    pass


class AssetState(StrEnum):
    UPLOADED = "uploaded"
    INSPECTING = "inspecting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"
    SOFT_DELETED = "soft_deleted"
    PURGE_PLANNED = "purge_planned"
    PURGED = "purged"


ASSET_TRANSITIONS = {
    AssetState.UPLOADED: {AssetState.INSPECTING, AssetState.REJECTED, AssetState.FAILED},
    AssetState.INSPECTING: {AssetState.ACCEPTED, AssetState.REJECTED, AssetState.FAILED},
    AssetState.ACCEPTED: {AssetState.PROCESSING, AssetState.FAILED},
    AssetState.PROCESSING: {AssetState.READY, AssetState.FAILED},
    AssetState.READY: {AssetState.ARCHIVED, AssetState.SOFT_DELETED},
    AssetState.FAILED: {AssetState.INSPECTING, AssetState.SOFT_DELETED},
    AssetState.ARCHIVED: {AssetState.READY, AssetState.SOFT_DELETED},
    AssetState.SOFT_DELETED: {AssetState.READY, AssetState.PURGE_PLANNED},
    AssetState.PURGE_PLANNED: {AssetState.SOFT_DELETED, AssetState.PURGED},
    AssetState.REJECTED: {AssetState.SOFT_DELETED},
    AssetState.PURGED: set(),
}


class UploadState(StrEnum):
    CREATED = "created"
    RECEIVING = "receiving"
    UPLOADED = "uploaded"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


UPLOAD_TRANSITIONS = {
    UploadState.CREATED: {UploadState.RECEIVING, UploadState.CANCELLED, UploadState.EXPIRED},
    UploadState.RECEIVING: {UploadState.UPLOADED, UploadState.CANCELLED, UploadState.EXPIRED, UploadState.FAILED},
    UploadState.UPLOADED: {UploadState.COMPLETED, UploadState.FAILED},
    UploadState.COMPLETED: set(),
    UploadState.EXPIRED: set(),
    UploadState.CANCELLED: set(),
    UploadState.FAILED: set(),
}


@dataclass(frozen=True)
class AssetSnapshot:
    asset_id: UUID
    site_id: str
    state: AssetState
    version: int
    has_blocking_reference: bool = False
    has_retention_hold: bool = False


@dataclass(frozen=True)
class UploadSnapshot:
    session_id: UUID
    site_id: str
    actor_ref: str
    expected_bytes: int
    received_bytes: int
    expected_sha256: str
    state: UploadState
    version: int
    expires_at: datetime


@dataclass(frozen=True)
class Quota:
    maximum_files: int
    maximum_batch_bytes: int
    maximum_object_bytes: int
    maximum_stored_bytes: int
    maximum_processing_jobs: int


@dataclass(frozen=True)
class DeliveryGrant:
    grant_id: UUID
    site_id: str
    asset_id: UUID
    object_version: int
    method: str
    audience_ref: str
    issued_at: datetime
    expires_at: datetime
    authorization_epoch: int


def _site(value: str) -> str:
    if not isinstance(value, str) or not SITE_ID.fullmatch(value):
        raise MediaLifecycleError("media_site_invalid")
    return value


def object_key(*, site_id: str, asset_id: UUID, object_version: int, sha256: str) -> str:
    _site(site_id)
    validate_digest(sha256)
    if not isinstance(asset_id, UUID) or not 1 <= object_version <= 2_147_483_647:
        raise MediaLifecycleError("media_object_identity_invalid")
    return f"media/{site_id}/{asset_id.hex}/v{object_version}/{sha256}.bin"


def transition_asset(
    snapshot: AssetSnapshot,
    *,
    target: AssetState,
    expected_version: int,
) -> AssetSnapshot:
    _site(snapshot.site_id)
    if expected_version != snapshot.version or expected_version < 1:
        raise MediaLifecycleError("media_version_conflict")
    if target not in ASSET_TRANSITIONS.get(snapshot.state, set()):
        raise MediaLifecycleError("media_transition_invalid")
    if target is AssetState.PURGE_PLANNED and (
        snapshot.has_blocking_reference or snapshot.has_retention_hold
    ):
        raise MediaLifecycleError("media_purge_blocked")
    if target is AssetState.PURGED and (
        snapshot.has_blocking_reference or snapshot.has_retention_hold
    ):
        raise MediaLifecycleError("media_purge_blocked")
    return replace(snapshot, state=target, version=snapshot.version + 1)


def transition_upload(
    snapshot: UploadSnapshot,
    *,
    target: UploadState,
    expected_version: int,
    observed_at: datetime,
) -> UploadSnapshot:
    _site(snapshot.site_id)
    if not ACTOR_REF.fullmatch(snapshot.actor_ref or ""):
        raise MediaLifecycleError("media_actor_invalid")
    validate_digest(snapshot.expected_sha256)
    if observed_at.tzinfo is None or snapshot.expires_at.tzinfo is None:
        raise MediaLifecycleError("media_time_invalid")
    if expected_version != snapshot.version or expected_version < 1:
        raise MediaLifecycleError("media_version_conflict")
    observed = observed_at.astimezone(UTC)
    expired = observed >= snapshot.expires_at.astimezone(UTC)
    if expired and target is not UploadState.EXPIRED:
        raise MediaLifecycleError("media_upload_expired")
    if target not in UPLOAD_TRANSITIONS.get(snapshot.state, set()):
        raise MediaLifecycleError("media_transition_invalid")
    if target in {UploadState.UPLOADED, UploadState.COMPLETED} and (
        snapshot.received_bytes != snapshot.expected_bytes
    ):
        raise MediaLifecycleError("media_upload_length_mismatch")
    return replace(snapshot, state=target, version=snapshot.version + 1)


def admit_quota(
    *,
    sizes: Iterable[int],
    stored_bytes: int,
    active_processing_jobs: int,
    quota: Quota,
) -> tuple[int, int]:
    values = list(sizes)
    numeric = (
        quota.maximum_files,
        quota.maximum_batch_bytes,
        quota.maximum_object_bytes,
        quota.maximum_stored_bytes,
        quota.maximum_processing_jobs,
        stored_bytes,
        active_processing_jobs,
    )
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in numeric):
        raise MediaLifecycleError("media_quota_invalid")
    if not values or len(values) > quota.maximum_files:
        raise MediaLifecycleError("media_quota_files_exceeded")
    if any(not isinstance(size, int) or isinstance(size, bool) or size < 1 for size in values):
        raise MediaLifecycleError("media_quota_invalid")
    if any(size > quota.maximum_object_bytes for size in values):
        raise MediaLifecycleError("media_quota_object_exceeded")
    batch = sum(values)
    if batch > quota.maximum_batch_bytes:
        raise MediaLifecycleError("media_quota_batch_exceeded")
    if stored_bytes + batch > quota.maximum_stored_bytes:
        raise MediaLifecycleError("media_quota_storage_exceeded")
    if active_processing_jobs + len(values) > quota.maximum_processing_jobs:
        raise MediaLifecycleError("media_quota_processing_exceeded")
    return len(values), batch


def validate_grant(
    grant: DeliveryGrant,
    *,
    observed_at: datetime,
    site_id: str,
    asset_id: UUID,
    object_version: int,
    method: str,
    audience_ref: str,
    authorization_epoch: int,
) -> None:
    _site(site_id)
    if method not in {"GET", "HEAD"} or grant.method not in {"GET", "HEAD"}:
        raise MediaLifecycleError("media_grant_method_invalid")
    if any(value.tzinfo is None for value in (grant.issued_at, grant.expires_at, observed_at)):
        raise MediaLifecycleError("media_time_invalid")
    lifetime = grant.expires_at.astimezone(UTC) - grant.issued_at.astimezone(UTC)
    if lifetime <= timedelta(0) or lifetime > timedelta(minutes=15):
        raise MediaLifecycleError("media_grant_lifetime_invalid")
    if not grant.issued_at <= observed_at < grant.expires_at:
        raise MediaLifecycleError("media_grant_expired")
    expected = (
        site_id, asset_id, object_version, method, audience_ref, authorization_epoch
    )
    actual = (
        grant.site_id, grant.asset_id, grant.object_version, grant.method,
        grant.audience_ref, grant.authorization_epoch,
    )
    if actual != expected:
        raise MediaLifecycleError("media_grant_scope_invalid")


def exact_dedup_identity(*, site_id: str, sha256: str) -> str:
    _site(site_id)
    validate_digest(sha256)
    return hashlib.sha256(f"media-dedup-v1\0{site_id}\0{sha256}".encode()).hexdigest()


def format_rule_for_detected_type(media_type: str):
    try:
        return FORMAT_RULES[media_type]
    except (KeyError, TypeError) as exc:
        raise MediaPolicyError("media_type_invalid") from exc
