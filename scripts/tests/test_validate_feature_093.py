import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "python" / "validate_feature_093.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_feature_093", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PlanningValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module()

    def test_accepts_minimal_valid_graph(self):
        text = """- [x] T001 [US1] Write spec | Depends: none | Validate: receipt
- [ ] T002 [US1] Implement | Depends: T001 | Validate: test
"""
        self.assertEqual([], self.validator.validate_task_graph(text))

    def test_rejects_duplicate_and_unknown_dependency(self):
        text = """- [ ] T001 [US1] A | Depends: T999 | Validate: test
- [ ] T001 [US1] B | Depends: none | Validate: test
"""
        findings = self.validator.validate_task_graph(text)
        self.assertTrue(any("duplicate" in finding for finding in findings))
        self.assertTrue(any("unknown dependency T999" in finding for finding in findings))

    def test_rejects_dependency_cycle(self):
        text = """- [ ] T001 [US1] A | Depends: T002 | Validate: test
- [ ] T002 [US1] B | Depends: T001 | Validate: test
"""
        self.assertTrue(any("cycle" in finding for finding in self.validator.validate_task_graph(text)))

    def test_rejects_checked_task_without_validation(self):
        text = "- [x] T001 [US1] A | Depends: none | Validate: none\n"
        self.assertTrue(any("checked" in finding for finding in self.validator.validate_task_graph(text)))

    def test_rejects_unmapped_requirement(self):
        spec_text = "- **FR-001**: One\n- **FR-002**: Two\n"
        trace_text = "| FR-001 | T001 | evidence |\n"
        self.assertEqual(["requirement FR-002 is not traced"], self.validator.validate_traceability(spec_text, trace_text))

    def test_accepts_prettier_aligned_traceability_table(self):
        spec_text = "- **FR-001**: One\n"
        trace_text = "| Requirement | Tasks |\n| ----------- | ----- |\n| FR-001      | T001  |\n"
        self.assertEqual([], self.validator.validate_traceability(spec_text, trace_text))

    def test_detects_placeholders_but_allows_resolved_history(self):
        docs = {"spec.md": "NEEDS CLARIFICATION", "analysis.md": "Pending.\nResult: Resolved"}
        findings = self.validator.validate_placeholders(docs)
        self.assertEqual(["spec.md contains unresolved placeholder: NEEDS CLARIFICATION"], findings)

    def test_rejects_live_activation_without_separate_approval(self):
        text = "- [ ] T001 [US1] Deploy to DigitalOcean | Depends: none | Validate: smoke\n"
        self.assertTrue(any("approval boundary" in finding for finding in self.validator.validate_task_graph(text)))


if __name__ == "__main__":
    unittest.main()
