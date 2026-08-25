import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.python.module_registry import ModuleContractError, ModuleRegistry, validate_manifest


def manifest(module_id='content', **changes):
    value = {
        'schemaVersion': 1,
        'id': module_id,
        'version': '1.2.3',
        'compatibility': '>=2.0.0,<3.0.0',
        'models': [f'{module_id}.entry'],
        'migrations': [f'modules/{module_id}/migrations/0001.sql'],
        'apiRoutes': [f'/api/modules/{module_id}'],
        'uiRoutes': [f'/{module_id}'],
        'navigation': [f'{module_id}.index'],
        'permissions': [f'{module_id}.read'],
        'jobs': [f'{module_id}.refresh'],
        'settingsSchema': f'modules/{module_id}/settings.schema.json',
        'healthChecks': [f'{module_id}.ready'],
        'providerCapabilities': [],
        'dependencies': [],
        'dataLifecycle': {'disable': 'preserve', 'export': True, 'remove': 'backup-required'},
    }
    value.update(changes)
    return value


class ModuleRegistryTests(unittest.TestCase):
    def test_public_fixture_installs_only_through_sdk_and_hostile_files_fail(self):
        root = Path(__file__).parents[2]
        fixture = json.loads(
            (root / 'modules/fixture-notes/module.json').read_text(encoding='utf-8')
        )
        registry = ModuleRegistry([fixture])
        self.assertEqual(['fixture-notes'], [item['id'] for item in registry.install_plan()])
        hostile_root = root / 'scripts/tests/fixtures/modules'
        for path in sorted(hostile_root.glob('hostile-*.json')):
            with self.subTest(path=path), self.assertRaises(ModuleContractError):
                validate_manifest(json.loads(path.read_text(encoding='utf-8')))

    def test_validates_and_normalizes_complete_manifest(self):
        result = validate_manifest(manifest())
        self.assertEqual('content', result.id)
        self.assertEqual('1.2.3', result.version)

    def test_rejects_invalid_schema_semantics_and_compatibility(self):
        mutations = [
            {'extra': True},
            {'schemaVersion': 2},
            {'id': '../bad'},
            {'version': 'latest'},
            {'compatibility': '>=3.0.0'},
            {'permissions': ['other.read']},
            {'providerCapabilities': ['shell']},
            {'migrations': ['../escape.sql']},
            {'settingsSchema': '/etc/passwd'},
            {'apiRoutes': ['/api//bad']},
            {'dataLifecycle': {'disable': 'drop', 'export': True, 'remove': 'purge'}},
        ]
        for changes in mutations:
            with self.subTest(changes=changes), self.assertRaises(ModuleContractError):
                validate_manifest(manifest(**changes))

    def test_rejects_duplicate_missing_cyclic_and_conflicting_modules(self):
        cases = [
            [manifest(), manifest()],
            [manifest(dependencies=['missing'])],
            [manifest('one', dependencies=['two']), manifest('two', dependencies=['one'])],
            [manifest('one'), manifest('two', apiRoutes=['/api/modules/one'])],
        ]
        for payloads in cases:
            with self.subTest(payloads=payloads), self.assertRaises(ModuleContractError):
                ModuleRegistry(payloads)

    def test_install_plan_is_dependency_ordered_and_data_only(self):
        registry = ModuleRegistry([
            manifest('blog', dependencies=['content'], providerCapabilities=['storage']),
            manifest('content'),
            manifest('search', dependencies=['content']),
        ])
        plan = registry.install_plan()
        self.assertEqual(['content', 'blog', 'search'], [item['id'] for item in plan])
        self.assertNotIn('command', json.dumps(plan).lower())
        self.assertEqual({'content', 'blog', 'search'}, set(registry.health_inventory()))

    def test_directory_loader_rejects_symlinks_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'content.json').write_text('{bad', encoding='utf-8')
            with self.assertRaises(ModuleContractError):
                ModuleRegistry.from_directory(root)
            (root / 'content.json').write_text(json.dumps(manifest()), encoding='utf-8')
            outside = root.parent / f'{root.name}-outside.json'
            outside.write_text(json.dumps(manifest('outside')), encoding='utf-8')
            self.addCleanup(outside.unlink, missing_ok=True)
            (root / 'linked.json').symlink_to(outside)
            with self.assertRaises(ModuleContractError):
                ModuleRegistry.from_directory(root)

    def test_input_is_deep_copied(self):
        payload = manifest()
        validated = validate_manifest(payload)
        payload['models'].append('content.changed')
        self.assertEqual(['content.entry'], validated.payload['models'])


if __name__ == '__main__':
    unittest.main()
