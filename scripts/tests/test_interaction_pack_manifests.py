import json
import unittest
from pathlib import Path

from scripts.python.module_registry import ModuleRegistry


class InteractionPackManifestTests(unittest.TestCase):
    def test_forms_media_gallery_dependency_and_capability_plan(self):
        root = Path(__file__).parents[2]
        manifests = [
            json.loads((root / f'modules/{name}/module.json').read_text(encoding='utf-8'))
            for name in ('gallery', 'forms', 'media')
        ]
        plan = ModuleRegistry(manifests).install_plan()
        self.assertEqual(['forms', 'media', 'gallery'], [item['id'] for item in plan])
        capabilities = {item['id']: item['capabilities'] for item in plan}
        self.assertEqual(['email'], capabilities['forms'])
        self.assertEqual(['storage'], capabilities['media'])
        self.assertEqual([], capabilities['gallery'])


if __name__ == '__main__':
    unittest.main()
