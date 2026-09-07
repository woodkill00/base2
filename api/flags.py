from __future__ import annotations

import hashlib
import os
import re
from datetime import UTC, datetime
from typing import Any

FLAG_ID = re.compile(r'^[a-z][a-z0-9.-]{2,62}$')
FLAG_FIELDS = {
    'schemaVersion',
    'id',
    'enabled',
    'environments',
    'rolloutPercent',
    'expiresAt',
    'revision',
}
FLAG_ENVIRONMENTS = {'development', 'test', 'preview', 'staging', 'production'}


class FlagError(ValueError):
    pass


def _flag_time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError) as exc:
        raise FlagError('flag:expiry_invalid') from exc
    if result.tzinfo is None:
        raise FlagError('flag:expiry_invalid')
    return result.astimezone(UTC)


def evaluate_flag(
    definition: Any,
    *,
    environment: str,
    tenant_id: str,
    subject_id: str,
    now: datetime,
) -> dict[str, Any]:
    if (
        not isinstance(definition, dict)
        or set(definition) != FLAG_FIELDS
        or definition.get('schemaVersion') != 1
        or not FLAG_ID.fullmatch(str(definition.get('id', '')))
        or type(definition.get('enabled')) is not bool
        or type(definition.get('revision')) is not int
        or definition['revision'] < 1
        or type(definition.get('rolloutPercent')) is not int
        or not 0 <= definition['rolloutPercent'] <= 100
    ):
        raise FlagError('flag:definition_invalid')
    environments = definition['environments']
    if (
        not isinstance(environments, list)
        or not environments
        or len(environments) != len(set(environments))
        or not set(environments) <= FLAG_ENVIRONMENTS
    ):
        raise FlagError('flag:environment_invalid')
    if environment not in FLAG_ENVIRONMENTS or now.tzinfo is None:
        raise FlagError('flag:context_invalid')
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', tenant_id or '') or not re.fullmatch(
        r'[A-Za-z0-9][A-Za-z0-9._:-]{2,127}', subject_id or ''
    ):
        raise FlagError('flag:context_invalid')
    expires_at = _flag_time(definition['expiresAt'])
    reason = 'enabled'
    active = definition['enabled']
    if now.astimezone(UTC) >= expires_at:
        active, reason = False, 'expired'
    elif environment not in environments:
        active, reason = False, 'environment-denied'
    bucket = (
        int.from_bytes(
            hashlib.sha256(
                f"{definition['id']}\0{definition['revision']}\0{tenant_id}\0{subject_id}".encode()
            ).digest()[:4],
            'big',
        )
        % 10_000
    )
    if active and bucket >= definition['rolloutPercent'] * 100:
        active, reason = False, 'rollout-denied'
    return {
        'id': definition['id'],
        'revision': definition['revision'],
        'enabled': active,
        'reason': reason,
        'bucket': bucket,
        'expiresAt': expires_at.isoformat(),
    }


def get_flags() -> dict[str, bool]:
    """Return backend feature flags.

    Current implementation is env-driven:
    - FEATURE_FLAGS=flag_a,flag_b enables listed flags
    - FLAG_<NAME>=true|false enables per-flag

    Flag names are normalized to lowercase.
    """

    flags: dict[str, bool] = {}

    raw_list = os.getenv('FEATURE_FLAGS', '')
    if raw_list:
        for part in raw_list.split(','):
            name = (part or '').strip().lower()
            if not name:
                continue
            flags[name] = True

    for k, v in os.environ.items():
        if not k.startswith('FLAG_'):
            continue
        name = k[len('FLAG_') :].strip().lower()
        if not name:
            continue
        enabled = str(v or '').strip().lower() in {'1', 'true', 'yes', 'on'}
        flags[name] = enabled

    return flags
