"""Pure replay-safe media operations shared by routes and fixed workers."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from api.services.media_library_policy import validate_digest


SAFE_CODE = re.compile(r'^media_[a-z0-9_]{3,63}$')


class MediaOperationError(ValueError):
    pass


class Scanner(Protocol):
    tool_ref: str
    definitions_at: datetime

    def inspect(self, content: bytes) -> dict[str, Any]: ...


class Decoder(Protocol):
    tool_ref: str

    def probe(self, content: bytes, media_type: str) -> dict[str, Any]: ...


class Transformer(Protocol):
    tool_ref: str

    def transform(self, content: bytes, recipe: dict[str, Any]) -> bytes: ...


@dataclass(frozen=True)
class ToolHealth:
    scanner_ref: str
    definitions_at: datetime
    decoder_ref: str
    observed_at: datetime


def admit_tools(health: ToolHealth, *, maximum_signature_age: timedelta) -> None:
    if (
        any(value.tzinfo is None for value in (health.definitions_at, health.observed_at))
        or not re.fullmatch(r'[a-z0-9_.-]+:[A-Za-z0-9._-]{1,48}', health.scanner_ref or '')
        or not re.fullmatch(r'[a-z0-9_.-]+:[A-Za-z0-9._-]{1,48}', health.decoder_ref or '')
        or maximum_signature_age <= timedelta(0)
        or maximum_signature_age > timedelta(days=7)
        or health.observed_at.astimezone(UTC) - health.definitions_at.astimezone(UTC)
        > maximum_signature_age
    ):
        raise MediaOperationError('media_scanner_stale')


@dataclass(frozen=True)
class PartReceipt:
    part_number: int
    sha256: str
    byte_size: int
    storage_key: str


@dataclass(frozen=True)
class MultipartSnapshot:
    site_id: str
    session_id: str
    expected_sha256: str
    expected_bytes: int
    status: str
    version: int
    expires_at: datetime
    parts: tuple[PartReceipt, ...] = ()
    terminal_digest: str = ''


def add_part(
    snapshot: MultipartSnapshot,
    *,
    receipt: PartReceipt,
    expected_version: int,
    observed_at: datetime,
    maximum_parts: int = 1_000,
) -> MultipartSnapshot:
    if snapshot.status not in {'created', 'receiving'}:
        raise MediaOperationError('media_upload_terminal')
    if expected_version != snapshot.version:
        raise MediaOperationError('media_version_conflict')
    if observed_at.tzinfo is None or observed_at >= snapshot.expires_at:
        raise MediaOperationError('media_upload_expired')
    validate_digest(receipt.sha256)
    if not 1 <= receipt.part_number <= maximum_parts or receipt.byte_size < 1:
        raise MediaOperationError('media_upload_part_invalid')
    existing = {part.part_number: part for part in snapshot.parts}
    if receipt.part_number in existing:
        if existing[receipt.part_number] == receipt:
            return snapshot
        raise MediaOperationError('media_upload_part_conflict')
    parts = tuple(sorted((*snapshot.parts, receipt), key=lambda item: item.part_number))
    if (
        len(parts) > maximum_parts
        or sum(item.byte_size for item in parts) > snapshot.expected_bytes
    ):
        raise MediaOperationError('media_upload_length_invalid')
    return replace(snapshot, status='receiving', version=snapshot.version + 1, parts=parts)


def complete_multipart(
    snapshot: MultipartSnapshot, *, expected_version: int, observed_at: datetime
) -> MultipartSnapshot:
    if snapshot.status == 'completed' and snapshot.terminal_digest:
        return snapshot
    if snapshot.status != 'receiving' or expected_version != snapshot.version:
        raise MediaOperationError('media_upload_state_invalid')
    if observed_at.tzinfo is None or observed_at >= snapshot.expires_at:
        raise MediaOperationError('media_upload_expired')
    if (
        not snapshot.parts
        or sum(part.byte_size for part in snapshot.parts) != snapshot.expected_bytes
    ):
        raise MediaOperationError('media_upload_length_invalid')
    if tuple(part.part_number for part in snapshot.parts) != tuple(
        range(1, len(snapshot.parts) + 1)
    ):
        raise MediaOperationError('media_upload_part_gap')
    terminal = hashlib.sha256(
        json.dumps(
            [part.__dict__ for part in snapshot.parts], sort_keys=True, separators=(',', ':')
        ).encode()
    ).hexdigest()
    return replace(
        snapshot, status='completed', version=snapshot.version + 1, terminal_digest=terminal
    )


def cancel_multipart(snapshot: MultipartSnapshot, *, expected_version: int) -> MultipartSnapshot:
    if snapshot.status == 'cancelled':
        return snapshot
    if (
        snapshot.status in {'completed', 'expired', 'failed'}
        or expected_version != snapshot.version
    ):
        raise MediaOperationError('media_upload_state_invalid')
    return replace(snapshot, status='cancelled', version=snapshot.version + 1)


def derivative_identity(
    *, source_sha256: str, recipe_id: str, recipe_version: int, processor_ref: str
) -> str:
    validate_digest(source_sha256)
    if (
        not re.fullmatch(r'[a-z][a-z0-9-]{2,63}', recipe_id or '')
        or not 1 <= recipe_version <= 2_147_483_647
        or not re.fullmatch(r'[a-z0-9_.-]+:[A-Za-z0-9._-]{1,48}', processor_ref or '')
    ):
        raise MediaOperationError('media_recipe_invalid')
    return hashlib.sha256(
        f'media-derivative-v1\0{source_sha256}\0{recipe_id}\0{recipe_version}\0{processor_ref}'.encode()
    ).hexdigest()


def similarity_suggestion(
    *, left_digest: str, right_digest: str, perceptual_distance: int, same_site: bool
) -> dict[str, Any] | None:
    validate_digest(left_digest)
    validate_digest(right_digest)
    if not same_site:
        return None
    if (
        not isinstance(perceptual_distance, int)
        or isinstance(perceptual_distance, bool)
        or not 0 <= perceptual_distance <= 64
    ):
        raise MediaOperationError('media_similarity_invalid')
    if left_digest == right_digest:
        return {'reason': 'exact_digest', 'confidence': 1.0, 'requiresReview': True}
    if perceptual_distance > 10:
        return None
    return {
        'reason': 'visual_similarity',
        'confidence': round(1 - perceptual_distance / 64, 4),
        'requiresReview': True,
    }


def neutralize_formula(value: Any) -> str:
    text = str(value).replace('\x00', '').replace('\r', ' ').replace('\n', ' ')[:2_000]
    return f"'{text}" if text.lstrip().startswith(('=', '+', '-', '@')) else text


def build_export(
    rows: list[dict[str, Any]], *, output_format: str, fields: tuple[str, ...]
) -> bytes:
    allowed = {
        'id',
        'filename',
        'mediaType',
        'byteSize',
        'sha256',
        'status',
        'visibility',
        'updatedAt',
    }
    if not fields or len(fields) != len(set(fields)) or set(fields) - allowed or len(rows) > 10_000:
        raise MediaOperationError('media_export_projection_invalid')
    projected = [{key: neutralize_formula(row.get(key, '')) for key in fields} for row in rows]
    if output_format == 'json':
        return json.dumps(
            projected, sort_keys=True, separators=(',', ':'), ensure_ascii=False
        ).encode()
    if output_format == 'csv':
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(projected)
        return stream.getvalue().encode()
    raise MediaOperationError('media_export_format_invalid')


def audit_hash(*, previous_hash: str, sequence: int, event: dict[str, Any]) -> str:
    validate_digest(previous_hash)
    if not 1 <= sequence <= 9_223_372_036_854_775_807 or not isinstance(event, dict):
        raise MediaOperationError('media_audit_invalid')
    encoded = json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    if len(encoded) > 16_384:
        raise MediaOperationError('media_audit_invalid')
    return hashlib.sha256(
        previous_hash.encode() + b'\0' + str(sequence).encode() + b'\0' + encoded
    ).hexdigest()


def verify_audit_chain(events: list[dict[str, Any]]) -> bool:
    previous = '0' * 64
    for expected_sequence, item in enumerate(events, start=1):
        if item.get('sequence') != expected_sequence or item.get('previousHash') != previous:
            return False
        content = item.get('event')
        try:
            calculated = audit_hash(
                previous_hash=previous, sequence=expected_sequence, event=content
            )
        except (ValueError, TypeError):
            return False
        if not isinstance(item.get('eventHash'), str) or not hmac.compare_digest(
            item['eventHash'], calculated
        ):
            return False
        previous = calculated
    return True


def destructive_preview(
    *,
    asset_id: str,
    references: list[dict[str, Any]],
    holds: list[dict[str, Any]],
    objects: list[dict[str, Any]],
) -> dict[str, Any]:
    if any(
        not isinstance(items, list) or len(items) > 128 for items in (references, holds, objects)
    ):
        raise MediaOperationError('media_preview_invalid')
    blocking = [
        item for item in references if item.get('required') or item.get('ownerState') == 'published'
    ]
    active_holds = [item for item in holds if item.get('active') is True]
    return {
        'assetId': asset_id,
        'allowed': not blocking and not active_holds,
        'blockingReferences': blocking,
        'activeHolds': active_holds,
        'objectCount': len(objects),
        'proposedEffects': [
            'revoke_delivery',
            'delete_derivatives',
            'delete_original',
            'retain_audit',
        ],
    }
