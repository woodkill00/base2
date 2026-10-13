"""Guard original reference images against unreviewed snapshot regeneration."""
import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class ReferenceContract(unittest.TestCase):
    def test_python_security_repairs_cover_all_deployment_consumers(self):
        expected = {
            'api/requirements.txt': ['pyjwt[crypto]==2.15.1', 'pypdf==6.19.0', 'urllib3==2.8.0'],
            'api/requirements-media-inspector.txt': ['pypdf==6.19.0'],
            'django/requirements.txt': ['django==6.1.1'],
            'digital_ocean/requirements.lock': ['pyjwt[crypto]==2.15.1', 'urllib3==2.8.0', 'oauthlib==4.0.0'],
        }
        for path, pins in expected.items():
            source = (ROOT / path).read_text()
            for pin in pins:
                self.assertIn(pin, source, path)

    def test_hardened_css_compiler_and_compatibility_are_selected(self):
        package = json.loads((ROOT / 'react-app/package.json').read_text())
        lock = json.loads((ROOT / 'react-app/package-lock.json').read_text())
        self.assertEqual(package['devDependencies']['tailwindcss'], '4.3.3')
        self.assertEqual(package['devDependencies']['@tailwindcss/postcss'], '4.3.3')
        self.assertEqual(package['dependencies']['axios'], '1.20.0')
        self.assertFalse(any(name.endswith('/braces') for name in lock['packages']))
        self.assertIn("'@tailwindcss/postcss'", (ROOT / 'react-app/postcss.config.js').read_text())
        css = (ROOT / 'react-app/src/index.css').read_text()
        self.assertIn("@config '../tailwind.config.js'", css)
        self.assertIn("@import 'tailwindcss/utilities.css'", css)
        self.assertNotIn('@tailwind base', css)

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
