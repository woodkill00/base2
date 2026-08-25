import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "python" / "security_result_adapter.py"
COMMIT = "a" * 40


def load_module():
    spec = importlib.util.spec_from_file_location("security_result_adapter", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sarif(level="none", score=None):
    result = {"level": level}
    if score is not None:
        result["properties"] = {"security-severity": score}
    return {"version": "2.1.0", "runs": [{"results": [result]}]}


class SecurityResultAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_module()

    def normalize(self, family, format_name, payload):
        raw = json.dumps(payload, sort_keys=True).encode()
        return self.adapter.normalize(family, format_name, payload, raw, "fixture", COMMIT)

    def test_secret_high_finding_fails(self):
        self.assertEqual("failed", self.normalize("secret", "sarif", sarif("error"))["status"])

    def test_sast_security_score_fails(self):
        result = self.normalize("sast", "sarif", sarif("warning", "8.1"))
        self.assertEqual(1, result["counts"]["high"])

    def test_dependency_high_count_fails(self):
        payload = {"metadata": {"vulnerabilities": {"critical": 0, "high": 1, "moderate": 0, "low": 0, "unknown": 0}}}
        self.assertEqual("failed", self.normalize("dependency", "npm-audit", payload)["status"])

    def test_sbom_malformed_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "CycloneDX"):
            self.normalize("sbom", "cyclonedx", {"bomFormat": "SPDX"})

    def test_provenance_tampered_digest_is_rejected(self):
        payload = {"predicateType": "https://slsa.dev/provenance/v1", "subject": [{"digest": {"sha256": "bad"}}]}
        with self.assertRaisesRegex(ValueError, "digest"):
            self.normalize("provenance", "slsa", payload)

    def test_image_high_finding_fails(self):
        self.assertEqual("failed", self.normalize("image", "sarif", sarif("error"))["status"])

    def test_dast_high_alert_fails(self):
        payload = {"site": [{"alerts": [{"riskcode": "3"}]}]}
        self.assertEqual("failed", self.normalize("dast", "zap", payload)["status"])

    def test_iac_failed_check_defaults_to_high_and_fails(self):
        payload = {"results": {"failed_checks": [{"check_id": "CKV_FIXTURE"}]}}
        self.assertEqual("failed", self.normalize("iac", "checkov", payload)["status"])

    def test_green_results_bind_raw_digest_and_commit(self):
        payload = {"version": "2.1.0", "runs": [{"results": []}]}
        result = self.normalize("secret", "sarif", payload)
        self.assertEqual("passed", result["status"])
        self.assertEqual(COMMIT, result["sourceCommit"])
        self.assertEqual(64, len(result["rawArtifactSha256"]))

    def test_policy_requires_all_families_and_blocking_high(self):
        policy_path = MODULE_PATH.parents[1] / "config" / "security-adapter-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        self.adapter.validate_policy(policy)
        del policy["families"]["dast"]
        with self.assertRaisesRegex(ValueError, "every family"):
            self.adapter.validate_policy(policy)

    def test_required_ci_families_are_wired_to_security_workflow(self):
        repo = MODULE_PATH.parents[2]
        policy = json.loads((repo / "scripts/config/security-adapter-policy.json").read_text(encoding="utf-8"))
        workflow = (repo / ".github/workflows/security.yml").read_text(encoding="utf-8")
        for family, entry in policy["families"].items():
            if entry["activation"] == "required-ci":
                self.assertIn(f"--family {family}", workflow)

    def test_inconsistent_normalized_counts_are_rejected(self):
        result = self.normalize("secret", "sarif", {"version": "2.1.0", "runs": [{"results": []}]})
        result["counts"]["total"] = 1
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            self.adapter.validate_result(result)


if __name__ == "__main__":
    unittest.main()
