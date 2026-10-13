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

    def test_approved_design_is_selected_by_deployment_and_release_matrices(self):
        reference = json.loads((HERE / 'reference.json').read_text())
        self.assertEqual(reference['ownerApproval'], 'approved')
        docker = (ROOT / 'react-app/Dockerfile').read_text()
        self.assertIn('ARG BASE2_VOLCANO_LAYOUT=true', docker)
        self.assertIn('ENV VITE_VOLCANO110_PREVIEW=${BASE2_VOLCANO_LAYOUT}', docker)
        for path in ('development.docker.yml', 'local.docker.yml'):
            self.assertIn('BASE2_VOLCANO_LAYOUT=${BASE2_VOLCANO_LAYOUT:-true}', (ROOT / path).read_text())
        for name in ('media-release', 'operations-release', 'workspace-release', 'restricted'):
            self.assertIn("VITE_VOLCANO110_PREVIEW: 'true'", (ROOT / f'react-app/playwright.{name}.config.mjs').read_text())
        gate = json.loads((ROOT / 'scripts/config/complete-gate-v1.json').read_text())
        check = next(c for c in gate['checks'] if c['id'] == 'feature-110-volcano')
        self.assertTrue(check['required'])


if __name__ == '__main__':
    unittest.main()
