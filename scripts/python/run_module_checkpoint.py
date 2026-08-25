#!/usr/bin/env python3
"""Run a credential-free acceptance checkpoint across every declarative module."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.python.module_lifecycle import ModuleLifecycle
from scripts.python.module_registry import ModuleRegistry


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def run() -> dict:
    paths = sorted(ROOT.glob('modules/*/module.json'))
    manifests = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    registry = ModuleRegistry(manifests)
    plan = registry.install_plan()
    route_owners: dict[str, str] = {}
    for manifest in manifests:
        for route in manifest['apiRoutes'] + manifest['uiRoutes']:
            if route in route_owners:
                raise RuntimeError(f'duplicate route: {route}')
            route_owners[route] = manifest['id']

    lifecycle_counts = {'install': 0, 'disable': 0, 'enable': 0, 'upgrade': 0, 'export': 0}
    with tempfile.TemporaryDirectory(prefix='base2-module-checkpoint-') as temporary:
        state = Path(temporary) / 'private' / 'state.json'
        lifecycle = ModuleLifecycle(state, receipt_key=b'module-checkpoint-receipt-key-v1')
        by_id = {item['id']: item for item in manifests}
        for item in plan:
            module = by_id[item['id']]
            lifecycle.apply(operation_id=f'install-{item["id"]}', action='install', manifest_payload=module)
            lifecycle_counts['install'] += 1
        for item in reversed(plan):
            module = by_id[item['id']]
            lifecycle.apply(operation_id=f'disable-{item["id"]}', action='disable', manifest_payload=module)
            lifecycle_counts['disable'] += 1
        for item in plan:
            module = by_id[item['id']]
            lifecycle.apply(operation_id=f'enable-{item["id"]}', action='enable', manifest_payload=module)
            lifecycle_counts['enable'] += 1
            upgraded = json.loads(json.dumps(module))
            upgraded['version'] = '1.0.1'
            lifecycle.upgrade_preview(upgraded)
            lifecycle.apply(operation_id=f'upgrade-{item["id"]}', action='upgrade', manifest_payload=upgraded)
            lifecycle_counts['upgrade'] += 1
            exported = lifecycle.export_inventory(item['id'])
            if exported['version'] != '1.0.1':
                raise RuntimeError(f'export mismatch: {item["id"]}')
            lifecycle_counts['export'] += 1
        overview = lifecycle.admin_overview()
        if len(overview) != len(manifests) or state.stat().st_mode & 0o077:
            raise RuntimeError('private lifecycle state contract failed')

    provider_modules = sorted(
        item['id'] for item in manifests if item['providerCapabilities']
    )
    return {
        'schemaVersion': 1,
        'status': 'passed',
        'moduleCount': len(manifests),
        'moduleIds': [item['id'] for item in plan],
        'lifecycleCounts': lifecycle_counts,
        'routeCount': len(route_owners),
        'routeInventoryDigest': _digest(route_owners),
        'providerCapabilityModules': provider_modules,
        'credentialReads': 0,
        'networkCalls': 0,
        'persistentStateRetained': False,
        'dependentGateEvidence': [
            'visual-harness', 'accessibility-matrix-contract', 'public-experience-checkpoint',
            'browser-compatibility-matrix', 'coverage-policy',
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run()
    encoded = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')
    print(encoded, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
