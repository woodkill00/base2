import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class NodeToolingCiTests(unittest.TestCase):
    def test_real_storybook_build_is_required_for_full_frontend_scope(self):
        workflow = (ROOT / '.github/workflows/ci-frontend.yml').read_text()
        self.assertIn('name: Build Storybook tooling compatibility', workflow)
        step = workflow.split('name: Build Storybook tooling compatibility', 1)[1].split('      - name:', 1)[0]
        self.assertIn("if: steps.scope.outputs.mode == 'full'", step)
        self.assertIn('timeout-minutes: 10', step)
        self.assertIn('run: npm run build-storybook', step)
        self.assertIn("STORYBOOK_DISABLE_TELEMETRY: '1'", step)
        self.assertNotIn('continue-on-error', step)
        self.assertNotIn('||', step)

    def test_existing_test_job_runs_tooling_regressions(self):
        package = json.loads((ROOT / 'react-app/package.json').read_text())
        self.assertEqual('npm run test:tooling', package['scripts']['pretest:ci'])
        self.assertIn('npm run verify:tooling', package['scripts']['test:tooling'])
        self.assertIn('--config=vitest.tooling.config.mjs', package['scripts']['test:tooling'])
        workflow = (ROOT / '.github/workflows/ci-frontend.yml').read_text()
        self.assertIn('run: npm run test:ci', workflow)

    def test_frontend_container_has_verified_patch_inputs_before_install(self):
        dockerfile = (ROOT / 'react-app/Dockerfile').read_text()
        install = dockerfile.index('RUN npm ci --legacy-peer-deps')
        for copy in (
            'COPY scripts/apply-tooling-compatibility.cjs scripts/tooling-compatibility.json ./scripts/',
            'COPY patches ./patches',
        ):
            self.assertLess(dockerfile.index(copy), install)
        self.assertNotIn('--ignore-scripts', dockerfile)

    def test_audit_still_includes_development_dependencies_at_moderate(self):
        workflow = (ROOT / '.github/workflows/security.yml').read_text()
        step = workflow.split('name: Audit frontend deps', 1)[1].split('      - name:', 1)[0]
        self.assertIn('npm audit --audit-level=moderate --json', step)
        self.assertNotIn('--omit', step)
        self.assertNotIn('continue-on-error', step)
        self.assertNotIn('||', step)


if __name__ == '__main__':
    unittest.main()
