from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "python" / "validate_supply_chain_policy.py"
POLICY_PATH = ROOT / "scripts" / "config" / "supply-chain-policy.json"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_supply_chain_policy", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generated_manifest():
    digest = "a" * 64
    return {
        "schemaVersion": 1,
        "sourceCommit": "b" * 40,
        "generator": "base2-factory-v1",
        "inputsDigest": "c" * 64,
        "artifactDigest": digest,
        "provenance": {
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": "child.tar", "digest": {"sha256": digest}}],
            "predicate": {"builder": {"id": "base2/factory"}, "buildType": "base2/child-v1"},
        },
        "verification": {
            "status": "verified",
            "signerIdentity": "base2-factory",
            "signatureDigest": "d" * 64,
        },
    }


class SupplyChainPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module()
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_repository_policy_is_valid(self):
        self.assertEqual([], self.validator.validate_policy(self.policy))

    def test_allowed_node_and_python_reports_pass(self):
        node = {"@scope/pkg@1.0.0": {"licenses": "MIT OR Apache-2.0"}}
        python = [{"Name": "fixture", "Version": "1.0", "License": "BSD-3-Clause"}]
        self.assertEqual([], self.validator.validate_license_report(node, "npm", self.policy))
        self.assertEqual([], self.validator.validate_license_report(python, "python", self.policy))

    def test_unknown_or_missing_license_fails(self):
        report = {
            "unknown@1.0.0": {"licenses": "UNKNOWN"},
            "missing@1.0.0": {},
        }
        findings = self.validator.validate_license_report(report, "npm", self.policy)
        self.assertEqual(2, len([item for item in findings if "unapproved or unknown" in item]))

    def test_forbidden_package_fails_even_with_allowed_license(self):
        node = {"event-stream@3.3.6": {"licenses": "MIT"}}
        python = [{"Name": "PyCrypto", "Version": "2.6", "License": "MIT"}]
        self.assertIn(
            "forbidden npm package: event-stream",
            self.validator.validate_license_report(node, "npm", self.policy),
        )
        self.assertIn(
            "forbidden python package: pycrypto",
            self.validator.validate_license_report(python, "python", self.policy),
        )

    def test_verified_generated_artifact_passes(self):
        self.assertEqual(
            [], self.validator.validate_generated_artifact(generated_manifest(), self.policy)
        )

    def test_unsigned_generated_artifact_fails(self):
        candidate = generated_manifest()
        candidate["verification"] = {"status": "unsigned"}
        findings = self.validator.validate_generated_artifact(candidate, self.policy)
        self.assertIn("generated artifact is unsigned or unverified", findings)

    def test_tampered_provenance_or_digest_fails(self):
        candidate = generated_manifest()
        candidate["artifactDigest"] = "e" * 64
        findings = self.validator.validate_generated_artifact(candidate, self.policy)
        self.assertIn("provenance subject does not bind artifactDigest", findings)

    def test_incomplete_policy_fails(self):
        candidate = copy.deepcopy(self.policy)
        candidate["generatedArtifact"]["requiredFields"].remove("verification")
        self.assertIn(
            "generatedArtifact requiredFields are incomplete",
            self.validator.validate_policy(candidate),
        )


if __name__ == "__main__":
    unittest.main()
