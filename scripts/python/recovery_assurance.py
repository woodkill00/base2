#!/usr/bin/env python3
"""Authenticated backup and isolated restore primitives for Base2 drills."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class RecoveryDenied(ValueError):
    pass


KEY_REF = re.compile(r'^vaultwarden://[A-Za-z0-9][A-Za-z0-9._/-]{2,254}$')
SAFE_TARGET = re.compile(r'^[a-z][a-z0-9-]{2,63}$')


def _encoded(value: bytes) -> str:
    return base64.b64encode(value).decode('ascii')


def _decoded(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise RecoveryDenied('backup:encoding_invalid') from exc


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_backup(*, payload: bytes, target_id: str, data_schema: int, key: bytes, key_ref: str, output: Path, now: datetime | None = None) -> dict[str, Any]:
    if not payload or len(payload) > 64 * 1024 * 1024:
        raise RecoveryDenied('backup:payload_invalid')
    if not SAFE_TARGET.fullmatch(target_id or '') or data_schema < 1:
        raise RecoveryDenied('backup:target_invalid')
    if len(key) != 32 or not KEY_REF.fullmatch(key_ref or ''):
        raise RecoveryDenied('backup:key_invalid')
    created = (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace('+00:00', 'Z')
    metadata = {'schemaVersion': 1, 'targetId': target_id, 'dataSchema': data_schema, 'createdAt': created, 'keyRef': key_ref}
    aad = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, payload, aad)
    envelope = {
        **metadata,
        'algorithm': 'AES-256-GCM',
        'nonce': _encoded(nonce),
        'ciphertext': _encoded(ciphertext),
        'plaintextSha256': hashlib.sha256(payload).hexdigest(),
        'plaintextSize': len(payload),
        'complete': True,
    }
    _atomic(output, envelope)
    return {
        'schemaVersion': 1,
        'targetId': target_id,
        'dataSchema': data_schema,
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'plaintextSha256': envelope['plaintextSha256'],
        'size': output.stat().st_size,
        'encrypted': True,
        'keyRef': key_ref,
        'createdAt': created,
    }


def restore_isolated(*, backup: Path, key: bytes, expected_target: str, expected_schema: int, output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise RecoveryDenied('restore:target_must_be_absent')
    try:
        envelope = json.loads(backup.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryDenied('restore:backup_invalid') from exc
    required = {'schemaVersion','targetId','dataSchema','createdAt','keyRef','algorithm','nonce','ciphertext','plaintextSha256','plaintextSize','complete'}
    if not isinstance(envelope, dict) or set(envelope) != required or envelope.get('schemaVersion') != 1 or envelope.get('complete') is not True:
        raise RecoveryDenied('restore:backup_invalid')
    if envelope['targetId'] != expected_target:
        raise RecoveryDenied('restore:wrong_target')
    if envelope['dataSchema'] != expected_schema:
        raise RecoveryDenied('restore:schema_mismatch')
    if len(key) != 32 or envelope['algorithm'] != 'AES-256-GCM':
        raise RecoveryDenied('restore:key_invalid')
    metadata = {name: envelope[name] for name in ('schemaVersion','targetId','dataSchema','createdAt','keyRef')}
    aad = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()
    try:
        plaintext = AESGCM(key).decrypt(_decoded(envelope['nonce']), _decoded(envelope['ciphertext']), aad)
    except Exception as exc:
        raise RecoveryDenied('restore:integrity_failed') from exc
    if len(plaintext) != envelope['plaintextSize'] or hashlib.sha256(plaintext).hexdigest() != envelope['plaintextSha256']:
        raise RecoveryDenied('restore:integrity_failed')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(plaintext)
        stream.flush()
        os.fsync(stream.fileno())
    return {'targetId': expected_target, 'dataSchema': expected_schema, 'sha256': hashlib.sha256(plaintext).hexdigest(), 'size': len(plaintext), 'isolated': True}


def migration_preflight(*, current_schema: int, target_schema: int, backup_schema: int) -> dict[str, Any]:
    if min(current_schema, target_schema, backup_schema) < 1:
        raise RecoveryDenied('migration:schema_invalid')
    if target_schema < current_schema:
        raise RecoveryDenied('migration:downgrade_denied')
    if backup_schema != current_schema:
        raise RecoveryDenied('migration:backup_stale')
    return {'allowed': True, 'fromSchema': current_schema, 'toSchema': target_schema, 'rollbackSchema': backup_schema}


def certificate_drill(*, acme_mode: str, days_remaining: int) -> dict[str, Any]:
    if acme_mode != 'staging':
        raise RecoveryDenied('certificate:production_forbidden')
    if days_remaining < 0:
        raise RecoveryDenied('certificate:expired')
    return {'mode': 'staging', 'renewalRequired': days_remaining <= 30, 'liveIssuance': False}


def preview_snapshot(*, lease_id: str, payload: bytes, key: bytes, key_ref: str, output: Path, verified_at: datetime, expires_at: datetime) -> dict[str, Any]:
    started = time.monotonic()
    receipt = create_backup(payload=payload, target_id=lease_id, data_schema=1, key=key, key_ref=key_ref, output=output, now=verified_at)
    if expires_at.astimezone(UTC) <= verified_at.astimezone(UTC):
        output.unlink(missing_ok=True)
        raise RecoveryDenied('snapshot:expiry_invalid')
    return {
        'schemaVersion': 1, 'leaseId': lease_id, 'status': 'complete',
        'sha256': receipt['sha256'], 'size': receipt['size'], 'encrypted': True,
        'keyRef': key_ref, 'verifiedAt': verified_at.astimezone(UTC).isoformat().replace('+00:00','Z'),
        'retentionExpiresAt': expires_at.astimezone(UTC).isoformat().replace('+00:00','Z'),
        'durationMs': round((time.monotonic() - started) * 1000, 3),
    }
