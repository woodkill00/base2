#!/usr/bin/env python3
"""Negative and positive tests for the Feature 104 planning validator."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_plan.py")
SPEC = importlib.util.spec_from_file_location("feature_104_validate_plan", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Feature 104 planning validator could not be loaded")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class Feature104PlanValidatorTests(unittest.TestCase):
    def test_current_plan_passes(self) -> None:
        self.assertEqual(validator.main(), 0)

    def test_missing_requirement_fails(self) -> None:
        spec = validator.read("spec.md").replace(
            "- **FR-062**: Implementation MUST proceed", "- Implementation MUST proceed", 1
        )
        with self.assertRaisesRegex(AssertionError, "FR-001..FR-062"):
            validator.validate_spec(spec)

    def test_task_gap_fails(self) -> None:
        tasks = validator.read("tasks.md").replace("- [ ] T076 ", "- [ ] T175 ", 1)
        with self.assertRaisesRegex(AssertionError, "contiguous"):
            validator.validate_tasks(tasks)

    def test_guarded_lifecycle_completion_fails(self) -> None:
        tasks = validator.read("tasks.md").replace("- [ ] T142 ", "- [x] T142 ", 1)
        with self.assertRaisesRegex(AssertionError, "may not be pre-completed"):
            validator.validate_tasks(tasks)

    def test_missing_traceability_row_fails(self) -> None:
        traceability = re.sub(
            r"^\|\s*FR-062\s*\|.*\n?",
            "",
            validator.read("traceability.md"),
            count=1,
            flags=re.MULTILINE,
        )
        with self.assertRaisesRegex(AssertionError, "traceability rows"):
            validator.validate_traceability(traceability)

    def test_missing_test_column_reference_fails(self) -> None:
        traceability = re.sub(
            r"^\|\s*FR-001\s*\|[^|]*\|[^|]*\|[^|]*\|\s*$",
            "| FR-001 | T079-T081 | none | T083, T140 |",
            validator.read("traceability.md"),
            count=1,
            flags=re.MULTILINE,
        )
        with self.assertRaisesRegex(AssertionError, "no test task reference"):
            validator.validate_traceability(traceability)

    def test_unresolved_marker_fails(self) -> None:
        documents = {relative: validator.read(relative) for relative in validator.REQUIRED_FILES}
        documents["analysis.md"] += "\nTODO: unresolved test marker\n"
        with self.assertRaisesRegex(AssertionError, "unresolved planning marker"):
            validator.validate_cross_document_contract(documents)


if __name__ == "__main__":
    unittest.main(verbosity=2)
