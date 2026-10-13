"""Guard original reference images against unreviewed snapshot regeneration."""
import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class ReferenceContract(unittest.TestCase):
    def test_complete_original_reference_is_unchanged(self):
        reference = json.loads((HERE / 'reference.json').read_text())
        expected = {f'volcano-{width}-{state}-chromium-linux.png'
                    for width in (390, 1440)
                    for state in ('home', 'left', 'right', 'palette')}
        self.assertEqual(set(reference['screenshots']), expected)
        directory = ROOT / 'react-app/e2e/layout/volcano-preservation.spec.ts-snapshots'
        for name, digest in reference['screenshots'].items():
            self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest,
                             f'Original visual reference changed: {name}; owner review required')

    def test_no_implicit_production_activation(self):
        for path in ('react-app/Dockerfile', 'development.docker.yml', 'local.docker.yml'):
            self.assertNotIn('VITE_VOLCANO110_PREVIEW', (ROOT / path).read_text())


if __name__ == '__main__':
    unittest.main()
