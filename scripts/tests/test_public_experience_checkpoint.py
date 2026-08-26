from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[2]


class PublicExperienceCheckpointTests(TestCase):
    def test_ledger_has_zero_unresolved_public_controls(self):
        ledger = (ROOT / 'specs/093-base2-foundation-hardening/experience-inventory.md').read_text()
        self.assertIn('zero unexplained public controls', ledger)
        for unresolved in ('Replace with', 'T069 will', 'require explicit route/control coverage'):
            self.assertNotIn(unresolved, ledger)

    def test_build_enforces_explicit_budgets(self):
        vite = (ROOT / 'react-app/vite.config.mjs').read_text()
        for marker in (
            'javascriptChunkBytes: 460 * 1024',
            'stylesheetBytes: 40 * 1024',
            'totalInitialBytes: 540 * 1024',
            'gzipSync(Buffer.from(payload)).byteLength',
            'performance_budget_javascript',
            'performance_budget_stylesheet',
            'performance_budget_total',
        ):
            self.assertIn(marker, vite)

    def test_checkpoint_links_required_matrices(self):
        document = (ROOT / 'docs/PUBLIC_EXPERIENCE_ACCEPTANCE.md').read_text()
        for marker in (
            'Chromium',
            'Firefox',
            'WebKit',
            'keyboard',
            'touch',
            'reduced motion',
            'screen-reader',
            'provider activation remains prohibited',
        ):
            self.assertIn(marker, document)
