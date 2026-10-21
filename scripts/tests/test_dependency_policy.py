import copy
import json
from datetime import date
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "python" / "validate_dependency_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_dependency_policy", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_policy():
    return {
        "schemaVersion": 1,
        "severityPolicy": {
            "critical": {"blocks": True, "remediationHours": 0, "exceptionsAllowed": False},
            "high": {"blocks": True, "remediationHours": 72, "exceptionsAllowed": False},
            "moderate": {"blocks": False, "remediationHours": 720, "exceptionsAllowed": True},
            "low": {"blocks": False, "remediationHours": 2160, "exceptionsAllowed": True},
        },
        "exceptionMaximumDays": 30,
        "exceptions": [],
    }


def exception():
    return {"id": "DEP-001", "ecosystem": "npm", "package": "fixture", "advisory": "ADV-1", "severity": "moderate", "owner": "security", "rationale": "fixture", "mitigation": "disabled path", "approvedBy": "owner", "reviewOn": "2026-08-25", "expiresOn": "2026-09-01"}


class DependencyPolicyTests(unittest.TestCase):
    def test_october_security_pins_cover_api_inspector_and_frontend(self):
        root = MODULE_PATH.parents[2]
        for path in ('api/requirements.in', 'api/requirements.txt',
                     'api/requirements-media-inspector.txt'):
            self.assertRegex((root / path).read_text(), r'(?im)^pillow==13\.0\.0(?:\s|$)')
            self.assertIn('pypdf==6.21.2', (root / path).read_text())
        self.assertIn('certifi==2026.10.19', (root / 'api/requirements.txt').read_text())
        lock = json.loads((root / 'react-app/package-lock.json').read_text())
        self.assertEqual('6.4.5', lock['packages']['node_modules/vite']['version'])
        for name in ('storybook', '@storybook/core'):
            self.assertEqual('8.6.19', lock['packages'][f'node_modules/{name}']['version'])
        redirects = [entry['version'] for name, entry in lock['packages'].items()
                     if name.endswith('node_modules/follow-redirects')]
        self.assertTrue(redirects)
        self.assertNotIn('1.16.0', redirects)
        inspector = (root / 'api/requirements-media-inspector.txt').read_text()
        self.assertRegex(inspector, r'pillow==13\.0\.0\s+\\\s+--hash=sha256:[a-f0-9]{64}')

    @classmethod
    def setUpClass(cls):
        cls.validator = load_module()

    def test_accepts_policy_without_exceptions(self):
        self.assertEqual([], self.validator.validate(base_policy(), today=date(2026, 8, 24)))

    def test_rejects_nonblocking_high_policy(self):
        candidate = base_policy()
        candidate["severityPolicy"]["high"]["blocks"] = False
        self.assertTrue(any("high" in item for item in self.validator.validate(candidate)))

    def test_rejects_high_exception(self):
        candidate = base_policy()
        item = exception()
        item["severity"] = "high"
        candidate["exceptions"] = [item]
        self.assertTrue(any("forbidden severity" in finding for finding in self.validator.validate(candidate, today=date(2026, 8, 24))))

    def test_rejects_ownerless_expired_exception(self):
        candidate = base_policy()
        item = exception()
        item["owner"] = ""
        item["expiresOn"] = "2026-08-23"
        candidate["exceptions"] = [item]
        findings = self.validator.validate(candidate, today=date(2026, 8, 24))
        self.assertTrue(any("lacks owner" in finding for finding in findings))
        self.assertTrue(any("expired" in finding for finding in findings))

    def test_rejects_overlong_or_overdue_exception(self):
        candidate = base_policy()
        item = exception()
        item["reviewOn"] = "2026-08-23"
        item["expiresOn"] = "2026-10-01"
        candidate["exceptions"] = [item]
        findings = self.validator.validate(candidate, today=date(2026, 8, 24))
        self.assertTrue(any("overdue" in finding for finding in findings))
        self.assertTrue(any("maximum duration" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
