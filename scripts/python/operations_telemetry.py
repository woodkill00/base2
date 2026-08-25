#!/usr/bin/env python3
"""Structured, redacted telemetry and idempotent local incident alerts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TelemetryError(ValueError):
    pass


CORRELATION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$')
SECRET_KEY = re.compile(r'(token|password|secret|credential|private.?key|authorization)', re.I)
SECRET_VALUE = re.compile(r'(?i)(bearer\s+\S+|(?:token|password|secret)\s*[=:]\s*\S+)')
EVENT_KINDS = {'request', 'queue', 'adapter', 'health', 'incident', 'recovery'}
LEVELS = {'info', 'warning', 'error'}


def _redact(value: Any, key: str = '') -> Any:
    if SECRET_KEY.search(key):
        return '[REDACTED]'
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value[:100]]
    if isinstance(value, str):
        return SECRET_VALUE.sub('[REDACTED]', value[:2048])
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:2048]


def event(*, kind: str, level: str, code: str, correlation_id: str, attributes: dict[str, Any]) -> dict[str, Any]:
    if kind not in EVENT_KINDS or level not in LEVELS:
        raise TelemetryError('telemetry:classification_invalid')
    if not re.fullmatch(r'[a-z][a-z0-9_.-]{2,95}', code or ''):
        raise TelemetryError('telemetry:code_invalid')
    if not CORRELATION.fullmatch(correlation_id or ''):
        raise TelemetryError('telemetry:correlation_invalid')
    if not isinstance(attributes, dict) or len(attributes) > 64:
        raise TelemetryError('telemetry:attributes_invalid')
    return {
        'schemaVersion': 1,
        'kind': kind,
        'level': level,
        'code': code,
        'correlationId': correlation_id,
        'attributes': _redact(attributes),
    }


class AlertLedger:
    def __init__(self, path: Path):
        self.path = path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {'schemaVersion': 1, 'incidents': {}}
        if self.path.is_symlink() or not self.path.is_file():
            raise TelemetryError('alerts:unsafe_state')
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TelemetryError('alerts:state_invalid') from exc
        if not isinstance(value, dict) or value.get('schemaVersion') != 1 or not isinstance(value.get('incidents'), dict):
            raise TelemetryError('alerts:state_invalid')
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=f'.{self.path.name}.', dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, sort_keys=True, separators=(',', ':'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def observe(self, *, incident_id: str, failing: bool, code: str) -> dict[str, Any]:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', incident_id or ''):
            raise TelemetryError('alerts:incident_invalid')
        if not re.fullmatch(r'[a-z][a-z0-9_.-]{2,95}', code or ''):
            raise TelemetryError('alerts:code_invalid')
        value = self._load()
        prior = value['incidents'].get(incident_id)
        target = 'firing' if failing else 'recovered'
        notify = prior is None or prior['state'] != target
        value['incidents'][incident_id] = {
            'state': target, 'code': code, 'notifications': int(prior['notifications']) + 1 if notify and prior else int(notify)
        }
        self._write(value)
        return {'incidentId': incident_id, 'state': target, 'notify': notify, 'code': code}


def diagnostic_bundle(*, source_commit: str, boot_id: str, events: list[dict[str, Any]], health: dict[str, str], queues: dict[str, int], adapters: dict[str, str]) -> dict[str, Any]:
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit or ''):
        raise TelemetryError('diagnostic:commit_invalid')
    if not CORRELATION.fullmatch(boot_id or ''):
        raise TelemetryError('diagnostic:boot_invalid')
    if len(events) > 1000 or any(item.get('schemaVersion') != 1 for item in events):
        raise TelemetryError('diagnostic:events_invalid')
    payload = {
        'schemaVersion': 1,
        'generatedAt': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'sourceCommit': source_commit,
        'bootId': boot_id,
        'events': _redact(events),
        'health': _redact(health),
        'queues': _redact(queues),
        'adapters': _redact(adapters),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    payload['digest'] = hashlib.sha256(canonical).hexdigest()
    return payload
