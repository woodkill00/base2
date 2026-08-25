#!/usr/bin/env python3
"""Validate Base2 module manifests and produce data-only install plans."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


MODULE_ID = re.compile(r'^[a-z][a-z0-9-]{1,62}$')
VERSION = re.compile(r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
PERMISSION = re.compile(r'^[a-z][a-z0-9-]{1,62}\.[a-z][a-z0-9:_-]{1,95}$')
SYMBOL = re.compile(r'^[a-z][a-z0-9_.-]{1,127}$')
CAPABILITIES = frozenset({'network', 'email', 'storage', 'payment', 'analytics', 'publish'})
REQUIRED = frozenset({
    'schemaVersion', 'id', 'version', 'compatibility', 'models', 'migrations',
    'apiRoutes', 'uiRoutes', 'navigation', 'permissions', 'jobs',
    'settingsSchema', 'healthChecks', 'providerCapabilities', 'dependencies',
    'dataLifecycle',
})
LIFECYCLE_KEYS = frozenset({'disable', 'export', 'remove'})


class ModuleContractError(ValueError):
    """A stable, non-secret module validation failure."""


def _version(value: str, field: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ModuleContractError(f'{field}:invalid_semver')
    return tuple(int(part) for part in value.split('.'))  # type: ignore[return-value]


def _safe_reference(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ModuleContractError(f'{field}:unsafe_reference')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or value.startswith('.'):
        raise ModuleContractError(f'{field}:unsafe_reference')
    return value


def _unique_strings(payload: dict[str, Any], field: str) -> tuple[str, ...]:
    value = payload[field]
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ModuleContractError(f'{field}:expected_string_list')
    if len(value) != len(set(value)):
        raise ModuleContractError(f'{field}:duplicate')
    return tuple(value)


def _compatible(specifier: str, base_version: str) -> bool:
    current = _version(base_version, 'baseVersion')
    clauses = [item.strip() for item in specifier.split(',') if item.strip()]
    if not clauses:
        raise ModuleContractError('compatibility:empty')
    for clause in clauses:
        match = re.fullmatch(r'(>=|<=|>|<|==)([0-9]+\.[0-9]+\.[0-9]+)', clause)
        if not match:
            raise ModuleContractError('compatibility:invalid_specifier')
        target = _version(match.group(2), 'compatibility')
        operator = match.group(1)
        if not {
            '>=': current >= target, '<=': current <= target, '>': current > target,
            '<': current < target, '==': current == target,
        }[operator]:
            return False
    return True


@dataclass(frozen=True)
class ModuleManifest:
    payload: dict[str, Any]

    @property
    def id(self) -> str:
        return self.payload['id']

    @property
    def version(self) -> str:
        return self.payload['version']

    @property
    def dependencies(self) -> tuple[str, ...]:
        return tuple(self.payload['dependencies'])


def validate_manifest(payload: Any, *, base_version: str = '2.0.0') -> ModuleManifest:
    if not isinstance(payload, dict):
        raise ModuleContractError('manifest:expected_object')
    keys = frozenset(payload)
    if keys != REQUIRED:
        missing = sorted(REQUIRED - keys)
        unknown = sorted(keys - REQUIRED)
        raise ModuleContractError(f'manifest:keys:missing={missing}:unknown={unknown}')
    if payload['schemaVersion'] != 1:
        raise ModuleContractError('schemaVersion:unsupported')
    module_id = payload['id']
    if not isinstance(module_id, str) or not MODULE_ID.fullmatch(module_id):
        raise ModuleContractError('id:invalid')
    _version(payload['version'], 'version')
    if not isinstance(payload['compatibility'], str) or not _compatible(
        payload['compatibility'], base_version
    ):
        raise ModuleContractError('compatibility:base_version_rejected')

    for field in ('models', 'navigation', 'jobs', 'healthChecks'):
        values = _unique_strings(payload, field)
        if any(not SYMBOL.fullmatch(value) for value in values):
            raise ModuleContractError(f'{field}:invalid_symbol')
    for field in ('migrations',):
        for index, value in enumerate(_unique_strings(payload, field)):
            _safe_reference(value, f'{field}[{index}]')
    _safe_reference(payload['settingsSchema'], 'settingsSchema')
    for field in ('apiRoutes', 'uiRoutes'):
        routes = _unique_strings(payload, field)
        if any(not route.startswith('/') or '//' in route or '..' in route for route in routes):
            raise ModuleContractError(f'{field}:unsafe_route')
    permissions = _unique_strings(payload, 'permissions')
    if any(not PERMISSION.fullmatch(value) or not value.startswith(f'{module_id}.') for value in permissions):
        raise ModuleContractError('permissions:not_namespaced')
    capabilities = _unique_strings(payload, 'providerCapabilities')
    if not set(capabilities) <= CAPABILITIES:
        raise ModuleContractError('providerCapabilities:unknown')
    dependencies = _unique_strings(payload, 'dependencies')
    if module_id in dependencies or any(not MODULE_ID.fullmatch(value) for value in dependencies):
        raise ModuleContractError('dependencies:invalid')
    lifecycle = payload['dataLifecycle']
    if not isinstance(lifecycle, dict) or frozenset(lifecycle) != LIFECYCLE_KEYS:
        raise ModuleContractError('dataLifecycle:invalid_keys')
    if lifecycle['disable'] not in {'preserve', 'archive'}:
        raise ModuleContractError('dataLifecycle:disable_invalid')
    if type(lifecycle['export']) is not bool:
        raise ModuleContractError('dataLifecycle:export_invalid')
    if lifecycle['remove'] not in {'forbid', 'backup-required', 'purge'}:
        raise ModuleContractError('dataLifecycle:remove_invalid')
    return ModuleManifest(json.loads(json.dumps(payload, sort_keys=True)))


class ModuleRegistry:
    def __init__(self, manifests: Iterable[dict[str, Any]], *, base_version: str = '2.0.0'):
        validated = [validate_manifest(item, base_version=base_version) for item in manifests]
        self._modules: dict[str, ModuleManifest] = {}
        for manifest in validated:
            if manifest.id in self._modules:
                raise ModuleContractError(f'module:duplicate:{manifest.id}')
            self._modules[manifest.id] = manifest
        self._validate_dependencies()
        self._validate_conflicts()
        self._order = self._topological_order()

    @classmethod
    def from_directory(cls, root: Path, *, base_version: str = '2.0.0') -> 'ModuleRegistry':
        if root.is_symlink() or not root.is_dir():
            raise ModuleContractError('registry:unsafe_root')
        payloads = []
        for path in sorted(root.glob('*.json')):
            if path.is_symlink() or not path.is_file():
                raise ModuleContractError('registry:unsafe_manifest')
            try:
                payloads.append(json.loads(path.read_text(encoding='utf-8')))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ModuleContractError(f'registry:unreadable:{path.name}') from exc
        return cls(payloads, base_version=base_version)

    def _validate_dependencies(self) -> None:
        for manifest in self._modules.values():
            for dependency in manifest.dependencies:
                if dependency not in self._modules:
                    raise ModuleContractError(f'dependency:missing:{manifest.id}:{dependency}')

    def _validate_conflicts(self) -> None:
        owners: dict[tuple[str, str], str] = {}
        for module_id in sorted(self._modules):
            payload = self._modules[module_id].payload
            for field in ('models', 'apiRoutes', 'uiRoutes', 'jobs', 'permissions'):
                for value in payload[field]:
                    key = (field, value)
                    if key in owners:
                        raise ModuleContractError(
                            f'conflict:{field}:{value}:{owners[key]}:{module_id}'
                        )
                    owners[key] = module_id

    def _topological_order(self) -> tuple[str, ...]:
        remaining = {key: set(value.dependencies) for key, value in self._modules.items()}
        ordered: list[str] = []
        while remaining:
            ready = sorted(key for key, deps in remaining.items() if not deps)
            if not ready:
                raise ModuleContractError(f'dependency:cycle:{sorted(remaining)}')
            for key in ready:
                ordered.append(key)
                remaining.pop(key)
            for deps in remaining.values():
                deps.difference_update(ready)
        return tuple(ordered)

    def install_plan(self) -> list[dict[str, Any]]:
        return [
            {
                'id': module_id,
                'version': self._modules[module_id].version,
                'migrations': list(self._modules[module_id].payload['migrations']),
                'capabilities': list(self._modules[module_id].payload['providerCapabilities']),
                'healthChecks': list(self._modules[module_id].payload['healthChecks']),
            }
            for module_id in self._order
        ]

    def health_inventory(self) -> dict[str, list[str]]:
        return {
            module_id: list(self._modules[module_id].payload['healthChecks'])
            for module_id in self._order
        }
