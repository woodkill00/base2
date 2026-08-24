from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "python" / "validate_threat_model.py"
MODEL_PATH = ROOT / "docs" / "THREAT_MODEL.md"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_threat_model", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ThreatModelPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module()
        cls.text = MODEL_PATH.read_text(encoding="utf-8")

    def test_repository_model_is_complete(self):
        self.assertEqual([], self.validator.validate(self.text))

    def test_missing_boundary_fails(self):
        candidate = "\n".join(
            line for line in self.text.splitlines() if not line.startswith("| provider |")
        )
        self.assertIn("missing threat boundary provider", self.validator.validate(candidate))

    def test_blank_control_or_owner_fails(self):
        candidate = self.text.replace("| application-security |", "|  |", 1)
        self.assertTrue(
            any("public lacks owner" in item for item in self.validator.validate(candidate))
        )

    def test_unknown_or_duplicate_boundary_fails(self):
        row = next(
            line
            for line in self.text.splitlines()
            if line.startswith("|") and self.validator._cells(line)[0] == "public"
        )
        candidate = self.text.replace(row, f'{row}\n{row}\n{row.replace("public", "unknown", 1)}')
        findings = self.validator.validate(candidate)
        self.assertIn("duplicate threat boundary public", findings)
        self.assertIn("unknown threat boundary unknown", findings)

    def test_missing_policy_and_test_task_fail(self):
        candidate = self.text.replace("data—not instructions", "ordinary data", 1)
        candidate = candidate.replace("T056-T064,T067-T069,T115,T119-T122", "none", 1)
        findings = self.validator.validate(candidate)
        self.assertIn("missing threat-model policy: data—not instructions", findings)
        self.assertIn("public lacks executable test task", findings)


if __name__ == "__main__":
    unittest.main()
