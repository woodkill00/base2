from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from scripts.python.module_registry import validate_manifest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/python/production_readiness.py"
POLICY_PATH = ROOT / "shared/config/production-readiness-v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("production_readiness", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductionReadinessContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module()
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def findings(self, candidate):
        return self.validator.validate_policy(candidate, ROOT)

    def test_repository_policy_and_inventory_pass(self):
        self.assertEqual([], self.findings(self.policy))

    def test_unknown_top_level_field_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["unbounded"] = True
        self.assertTrue(any("policy fields" in item for item in self.findings(candidate)))

    def test_missing_environment_fails(self):
        candidate = copy.deepcopy(self.policy)
        del candidate["environments"]["test"]
        self.assertTrue(any("environment inventory" in item for item in self.findings(candidate)))

    def test_preview_production_certificate_mode_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["environments"]["preview"]["certificateMode"] = "production"
        self.assertIn(
            "non-production certificate mode is unsafe: preview",
            self.findings(candidate),
        )

    def test_nonproduction_authority_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["environments"]["staging"]["productionAuthority"] = True
        self.assertIn(
            "non-production profile has production authority: staging",
            self.findings(candidate),
        )

    def test_production_activation_must_remain_separate(self):
        candidate = copy.deepcopy(self.policy)
        candidate["environments"]["production"]["productionAuthority"] = True
        self.assertIn("production activation is not separately gated", self.findings(candidate))

    def test_module_inventory_drift_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["modules"].remove("support")
        self.assertTrue(any("modules inventory drift" in item for item in self.findings(candidate)))

    def test_workflow_inventory_drift_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["workflows"].append("unknown.yml")
        self.assertTrue(any("workflows inventory drift" in item for item in self.findings(candidate)))

    def test_missing_protected_action_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["protectedActions"].remove("mutate-dns")
        self.assertTrue(any("protected action" in item for item in self.findings(candidate)))

    def test_missing_absence_surface_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["capabilityAbsence"].remove("workers")
        self.assertTrue(any("capability absence" in item for item in self.findings(candidate)))

    def test_resource_timeout_outside_bounds_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["resourceDefaults"]["requestTimeoutSeconds"] = 0
        self.assertIn(
            "resource default outside bounds: requestTimeoutSeconds",
            self.findings(candidate),
        )

    def test_boolean_is_not_an_integer_limit(self):
        candidate = copy.deepcopy(self.policy)
        candidate["resourceDefaults"]["maxAttempts"] = True
        self.assertIn("resource default outside bounds: maxAttempts", self.findings(candidate))

    def test_release_fields_are_bound_to_schema(self):
        candidate = copy.deepcopy(self.policy)
        candidate["releaseRequiredFields"].remove("artifactDigest")
        self.assertIn("release fields differ from the v2 schema", self.findings(candidate))

    def test_planning_baseline_must_be_exact_commit(self):
        candidate = copy.deepcopy(self.policy)
        candidate["planningBaseline"] = "main"
        self.assertIn("planningBaseline must be an exact commit", self.findings(candidate))

    def test_repository_baseline_is_an_ancestor(self):
        self.assertTrue(
            self.validator.baseline_is_ancestor(self.policy["planningBaseline"], ROOT)
        )

    def test_all_inventory_modules_use_the_closed_manifest_contract(self):
        validated = set()
        for module_id in self.policy["modules"]:
            payload = json.loads(
                (ROOT / "modules" / module_id / "module.json").read_text(encoding="utf-8")
            )
            validated.add(validate_manifest(payload).id)
        self.assertEqual(set(self.policy["modules"]), validated)


if __name__ == "__main__":
    unittest.main()
