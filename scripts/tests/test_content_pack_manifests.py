import json
import unittest
from pathlib import Path

from scripts.python.module_registry import ModuleRegistry


class ContentPackManifestTests(unittest.TestCase):
    def test_three_content_packs_validate_together_without_conflicts(self):
        root = Path(__file__).parents[2]
        manifests = [
            json.loads((root / f'modules/{name}/module.json').read_text(encoding='utf-8'))
            for name in ('portfolio', 'blog', 'documentation')
        ]
        plan = ModuleRegistry(manifests).install_plan()
        self.assertEqual(['blog', 'documentation', 'portfolio'], [item['id'] for item in plan])
        self.assertTrue(all(item['capabilities'] == [] for item in plan))


if __name__ == '__main__':
    unittest.main()
