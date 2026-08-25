#!/usr/bin/env python3
"""Durable, receipt-bound lifecycle for validated Base2 modules."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scripts.python.module_registry import ModuleContractError, ModuleManifest, validate_manifest


class ModuleLifecycleError(ValueError):
    """A stable module lifecycle failure without sensitive state."""


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()


class ModuleLifecycle:
    def __init__(self, state_path: Path, *, receipt_key: bytes, base_version: str = '2.0.0'):
        if len(receipt_key) < 32:
            raise ModuleLifecycleError('receipt_key:too_short')
        self.state_path = state_path
        self.lock_path = state_path.with_suffix(f'{state_path.suffix}.lock')
        self.receipt_key = receipt_key
        self.base_version = base_version

    def _empty(self) -> dict[str, Any]:
        return {'schemaVersion': 1, 'modules': {}, 'operations': {}, 'history': []}

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._empty()
        if self.state_path.is_symlink() or not self.state_path.is_file():
            raise ModuleLifecycleError('state:unsafe_path')
        try:
            value = json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ModuleLifecycleError('state:unreadable') from exc
        if not isinstance(value, dict) or value.get('schemaVersion') != 1:
            raise ModuleLifecycleError('state:invalid')
        if not all(isinstance(value.get(key), expected) for key, expected in (
            ('modules', dict), ('operations', dict), ('history', list)
        )):
            raise ModuleLifecycleError('state:invalid')
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f'.{self.state_path.name}.', dir=self.state_path.parent
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, sort_keys=True, separators=(',', ':'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.state_path)
            os.chmod(self.state_path, 0o600)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def _receipt(self, operation_id: str, request_digest: str, before: Any, after: Any) -> dict[str, str]:
        receipt = {
            'operationId': operation_id,
            'requestDigest': request_digest,
            'beforeDigest': _digest(before),
            'afterDigest': _digest(after),
        }
        receipt['signature'] = hmac.new(
            self.receipt_key,
            json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode(),
            hashlib.sha256,
        ).hexdigest()
        return receipt

    def apply(
        self,
        *,
        operation_id: str,
        action: str,
        manifest_payload: dict[str, Any],
        backup_receipt: str | None = None,
    ) -> dict[str, Any]:
        if not operation_id or len(operation_id) > 128:
            raise ModuleLifecycleError('operation_id:invalid')
        try:
            manifest = validate_manifest(manifest_payload, base_version=self.base_version)
        except ModuleContractError as exc:
            raise ModuleLifecycleError(f'manifest:{exc}') from exc
        request = {
            'operationId': operation_id,
            'action': action,
            'manifest': manifest.payload,
            'backupReceipt': backup_receipt,
        }
        request_digest = _digest(request)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.lock_path.open('a+', encoding='utf-8') as lock:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = self._load()
            prior = state['operations'].get(operation_id)
            if prior:
                if prior['receipt']['requestDigest'] != request_digest:
                    raise ModuleLifecycleError('operation_id:request_mismatch')
                return copy.deepcopy(prior['receipt'])
            before = copy.deepcopy(state['modules'])
            self._transition(state['modules'], action, manifest, backup_receipt)
            receipt = self._receipt(operation_id, request_digest, before, state['modules'])
            state['operations'][operation_id] = {
                'receipt': receipt,
                'before': before,
                'rolledBack': False,
            }
            state['history'].append(receipt)
            self._write(state)
            return copy.deepcopy(receipt)

    def _transition(
        self,
        modules: dict[str, Any],
        action: str,
        manifest: ModuleManifest,
        backup_receipt: str | None,
    ) -> None:
        existing = modules.get(manifest.id)
        if action == 'install':
            if existing:
                raise ModuleLifecycleError('install:already_installed')
            modules[manifest.id] = {
                'version': manifest.version, 'status': 'enabled',
                'manifestDigest': _digest(manifest.payload), 'jobsScheduled': bool(manifest.payload['jobs']),
                'dataState': 'preserved', 'manifest': manifest.payload,
            }
        elif action == 'enable':
            if not existing or existing['status'] != 'disabled':
                raise ModuleLifecycleError('enable:invalid_state')
            existing['status'] = 'enabled'
            existing['jobsScheduled'] = bool(existing['manifest']['jobs'])
        elif action == 'disable':
            if not existing or existing['status'] != 'enabled':
                raise ModuleLifecycleError('disable:invalid_state')
            existing['status'] = 'disabled'
            existing['jobsScheduled'] = False
            existing['dataState'] = existing['manifest']['dataLifecycle']['disable'] + 'd'
        elif action == 'upgrade':
            if not existing or existing['status'] not in {'enabled', 'disabled'}:
                raise ModuleLifecycleError('upgrade:not_installed')
            if tuple(map(int, manifest.version.split('.'))) <= tuple(map(int, existing['version'].split('.'))):
                raise ModuleLifecycleError('upgrade:not_newer')
            existing.update(
                version=manifest.version,
                manifestDigest=_digest(manifest.payload),
                manifest=manifest.payload,
                jobsScheduled=existing['status'] == 'enabled' and bool(manifest.payload['jobs']),
            )
        elif action == 'remove':
            if not existing:
                raise ModuleLifecycleError('remove:not_installed')
            policy = existing['manifest']['dataLifecycle']['remove']
            if policy == 'forbid':
                raise ModuleLifecycleError('remove:forbidden')
            if policy == 'backup-required' and not backup_receipt:
                raise ModuleLifecycleError('remove:backup_required')
            del modules[manifest.id]
        else:
            raise ModuleLifecycleError('action:unsupported')

    def rollback(self, *, operation_id: str, receipt: dict[str, str]) -> dict[str, Any]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.lock_path.open('a+', encoding='utf-8') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = self._load()
            record = state['operations'].get(operation_id)
            stored = record.get('receipt') if isinstance(record, dict) else None
            if stored != receipt:
                raise ModuleLifecycleError('rollback:not_exact_latest_receipt')
            if record['rolledBack']:
                return copy.deepcopy(record['rollbackReceipt'])
            if not state['history'] or state['history'][-1] != stored:
                raise ModuleLifecycleError('rollback:not_exact_latest_receipt')
            unsigned = {key: stored[key] for key in ('operationId', 'requestDigest', 'beforeDigest', 'afterDigest')}
            expected = hmac.new(
                self.receipt_key,
                json.dumps(unsigned, sort_keys=True, separators=(',', ':')).encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, stored['signature']):
                raise ModuleLifecycleError('rollback:receipt_integrity')
            if _digest(state['modules']) != stored['afterDigest'] or _digest(record['before']) != stored['beforeDigest']:
                raise ModuleLifecycleError('rollback:state_integrity')
            current = copy.deepcopy(state['modules'])
            state['modules'] = copy.deepcopy(record['before'])
            rollback_receipt = self._receipt(
                f'rollback:{operation_id}', stored['signature'], current, state['modules']
            )
            record['rolledBack'] = True
            record['rollbackReceipt'] = rollback_receipt
            state['history'].append(rollback_receipt)
            self._write(state)
            return copy.deepcopy(rollback_receipt)

    def status(self) -> dict[str, Any]:
        return copy.deepcopy(self._load()['modules'])

    def export_inventory(self, module_id: str) -> dict[str, Any]:
        module = self._load()['modules'].get(module_id)
        if not module:
            raise ModuleLifecycleError('export:not_installed')
        if not module['manifest']['dataLifecycle']['export']:
            raise ModuleLifecycleError('export:forbidden')
        return {'moduleId': module_id, 'version': module['version'], 'dataState': module['dataState']}

    def upgrade_preview(self, manifest_payload: dict[str, Any]) -> dict[str, Any]:
        manifest = validate_manifest(manifest_payload, base_version=self.base_version)
        existing = self._load()['modules'].get(manifest.id)
        if not existing:
            raise ModuleLifecycleError('upgrade:not_installed')
        current = set(existing['manifest']['migrations'])
        proposed = set(manifest.payload['migrations'])
        if not current <= proposed:
            raise ModuleLifecycleError('upgrade:migration_history_removed')
        return {
            'moduleId': manifest.id,
            'fromVersion': existing['version'],
            'toVersion': manifest.version,
            'addedMigrations': sorted(proposed - current),
            'manifestDigest': _digest(manifest.payload),
        }

    def admin_overview(self) -> list[dict[str, Any]]:
        modules = self._load()['modules']
        return [
            {
                'id': module_id,
                'version': module['version'],
                'status': module['status'],
                'jobsScheduled': module['jobsScheduled'],
                'dataState': module['dataState'],
                'healthChecks': list(module['manifest']['healthChecks']),
                'providerCapabilities': list(module['manifest']['providerCapabilities']),
            }
            for module_id, module in sorted(modules.items())
        ]
