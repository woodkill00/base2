from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


SCHEMA_VERSION = 1
ALLOWED_CORRECTIONS = frozenset({'display_name', 'avatar_url', 'bio'})


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def receipt_digest(*, operation_id: str, tenant_id: str, user_id: str, payload: Any, key: str) -> str:
    if not key:
        raise ValueError('receipt_key_required')
    envelope = {
        'operation_id': operation_id,
        'payload': payload,
        'schema_version': SCHEMA_VERSION,
        'tenant_id': tenant_id,
        'user_id': user_id,
    }
    return hmac.new(key.encode(), canonical_json(envelope).encode(), hashlib.sha256).hexdigest()


def verify_receipt(
    *, operation_id: str, tenant_id: str, user_id: str, payload: Any, key: str, digest: str
) -> bool:
    expected = receipt_digest(
        operation_id=operation_id,
        tenant_id=tenant_id,
        user_id=user_id,
        payload=payload,
        key=key,
    )
    return hmac.compare_digest(expected, str(digest))


def validate_correction(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError('correction_required')
    if not set(value) <= ALLOWED_CORRECTIONS:
        raise ValueError('correction_field_not_allowed')
    result: dict[str, str] = {}
    limits = {'display_name': 120, 'avatar_url': 500, 'bio': 2000}
    for key, raw in value.items():
        if not isinstance(raw, str) or len(raw) > limits[key]:
            raise ValueError('correction_value_invalid')
        result[key] = raw
    return result


def isolated_restore_preview(
    *, payload: Any, expected_digest: str, receipt: dict[str, str], key: str,
    target: str = 'isolated-preview'
) -> Any:
    """Validate an export for an isolated preview without mutating live data."""
    if target != 'isolated-preview':
        raise ValueError('live_restore_forbidden')
    if not verify_receipt(
        operation_id=receipt['operation_id'],
        tenant_id=receipt['tenant_id'],
        user_id=receipt['user_id'],
        payload=payload,
        key=key,
        digest=expected_digest,
    ):
        raise ValueError('export_integrity_failed')
    # Round-trip creates an independent value and rejects non-JSON payloads.
    return json.loads(canonical_json(payload))
