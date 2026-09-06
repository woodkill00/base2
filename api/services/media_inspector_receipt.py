"""Canonical, authenticated receipts for the isolated media inspector."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

RECEIPT_SCHEMA = 'base2-media-inspection-v1'
SHA256 = re.compile(r'^[a-f0-9]{64}$')
SAFE_REF = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
PAYLOAD_KEYS = {
    'schemaVersion',
    'jobId',
    'nonce',
    'assetId',
    'objectVersion',
    'sourceSha256',
    'requestedMediaType',
    'observedMediaType',
    'decision',
    'scanner',
    'decoder',
    'measurements',
    'preview',
    'startedAt',
    'finishedAt',
}
SCANNER_KEYS = {'engine', 'version', 'definitionsVersion', 'definitionsAt', 'verdict'}
DECODER_KEYS = {'name', 'version', 'buildIdentity'}
PREVIEW_KEYS = {'mediaType', 'sha256', 'byteSize', 'width', 'height'}
MEASUREMENT_KEYS = {'pixels', 'frames', 'pages', 'durationSeconds', 'expandedBytes', 'streams'}


class InspectorReceiptError(ValueError):
    pass


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode(
        'ascii'
    )


def _raw_key(encoded: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode((encoded or '').encode('ascii'))
    except (ValueError, UnicodeEncodeError) as exc:
        raise InspectorReceiptError('media_inspector_attestation_unavailable') from exc
    if len(key) != 32:
        raise InspectorReceiptError('media_inspector_attestation_unavailable')
    return key


def load_signing_key(encoded: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_raw_key(encoded))


def load_verify_key(encoded: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(_raw_key(encoded))


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith('Z'):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise InspectorReceiptError('media_inspector_receipt_invalid') from exc
    return parsed.astimezone(UTC)


def _validate_payload(payload: Any) -> dict[str, Any]:
    if (
        not isinstance(payload, dict)
        or set(payload) != PAYLOAD_KEYS
        or payload.get('schemaVersion') != RECEIPT_SCHEMA
        or payload.get('decision') != 'accepted'
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    for name in ('jobId', 'nonce', 'assetId', 'requestedMediaType', 'observedMediaType'):
        if not isinstance(payload[name], str) or not 1 <= len(payload[name]) <= 128:
            raise InspectorReceiptError('media_inspector_receipt_invalid')
    if (
        not isinstance(payload['objectVersion'], int)
        or isinstance(payload['objectVersion'], bool)
        or payload['objectVersion'] < 1
        or not SHA256.fullmatch(str(payload['sourceSha256']))
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    scanner = payload['scanner']
    if (
        not isinstance(scanner, dict)
        or set(scanner) != SCANNER_KEYS
        or scanner.get('verdict') != 'clean'
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    for name in ('engine', 'version', 'definitionsVersion'):
        if not isinstance(scanner[name], str) or not SAFE_REF.fullmatch(scanner[name]):
            raise InspectorReceiptError('media_inspector_receipt_invalid')
    _timestamp(scanner['definitionsAt'])
    decoder = payload['decoder']
    if (
        not isinstance(decoder, dict)
        or set(decoder) != DECODER_KEYS
        or not SAFE_REF.fullmatch(str(decoder['name']))
        or not SAFE_REF.fullmatch(str(decoder['version']))
        or not re.fullmatch(r'base2-media-inspector:[a-f0-9]{64}', str(decoder['buildIdentity']))
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    measurements = payload['measurements']
    if (
        not isinstance(measurements, dict)
        or set(measurements) - MEASUREMENT_KEYS
        or len(measurements) > 6
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
        for value in measurements.values()
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    preview = payload['preview']
    if (
        not isinstance(preview, dict)
        or set(preview) != PREVIEW_KEYS
        or not isinstance(preview['mediaType'], str)
        or not SHA256.fullmatch(str(preview['sha256']))
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    if (
        not isinstance(preview['byteSize'], int)
        or isinstance(preview['byteSize'], bool)
        or not 1 <= preview['byteSize'] <= 10 * 1024 * 1024
    ):
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    for name in ('width', 'height'):
        if preview[name] is not None and (
            isinstance(preview[name], bool)
            or not isinstance(preview[name], int)
            or preview[name] < 1
        ):
            raise InspectorReceiptError('media_inspector_receipt_invalid')
    _timestamp(payload['startedAt'])
    _timestamp(payload['finishedAt'])
    return payload


def sign_receipt(payload: dict[str, Any], key: Ed25519PrivateKey) -> dict[str, Any]:
    encoded = canonical_bytes(_validate_payload(payload))
    return {
        'payload': payload,
        'resultSha256': hashlib.sha256(encoded).hexdigest(),
        'signature': base64.urlsafe_b64encode(key.sign(encoded)).decode('ascii'),
    }


def verify_receipt(
    receipt: Any,
    *,
    key: Ed25519PublicKey,
    expected_job_id: str,
    expected_nonce: str,
    expected_asset_id: str,
    expected_object_version: int,
    expected_source_sha256: str,
    expected_media_type: str,
    now: datetime,
    maximum_age: timedelta = timedelta(minutes=2),
) -> dict[str, Any]:
    if not isinstance(receipt, dict) or set(receipt) != {'payload', 'resultSha256', 'signature'}:
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    payload = _validate_payload(receipt['payload'])
    encoded = canonical_bytes(payload)
    digest = hashlib.sha256(encoded).hexdigest()
    if str(receipt['resultSha256']) != digest:
        raise InspectorReceiptError('media_inspector_receipt_invalid')
    try:
        signature = base64.urlsafe_b64decode(str(receipt['signature']).encode('ascii'))
        key.verify(signature, encoded)
    except (ValueError, UnicodeEncodeError, InvalidSignature) as exc:
        raise InspectorReceiptError('media_inspector_receipt_invalid') from exc
    expected = (
        (payload['jobId'], expected_job_id),
        (payload['nonce'], expected_nonce),
        (payload['assetId'], expected_asset_id),
        (payload['objectVersion'], expected_object_version),
        (payload['sourceSha256'], expected_source_sha256),
        (payload['requestedMediaType'], expected_media_type),
    )
    if any(actual != wanted for actual, wanted in expected):
        raise InspectorReceiptError('media_inspector_receipt_binding_invalid')
    started, finished, current = (
        _timestamp(payload['startedAt']),
        _timestamp(payload['finishedAt']),
        now.astimezone(UTC),
    )
    if (
        finished < started
        or finished > current + timedelta(seconds=5)
        or current - finished > maximum_age
    ):
        raise InspectorReceiptError('media_inspector_receipt_stale')
    definitions = _timestamp(payload['scanner']['definitionsAt'])
    if definitions > current + timedelta(seconds=5) or current - definitions > timedelta(hours=24):
        raise InspectorReceiptError('media_scanner_stale')
    return payload
