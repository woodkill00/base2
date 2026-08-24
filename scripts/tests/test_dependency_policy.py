import copy
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
