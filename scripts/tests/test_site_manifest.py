from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from api import site_manifest as api_runtime
from scripts.python.generate_site_profiles import generate
from scripts.python.site_manifest import (
    ManifestError,
    load_manifest,
    manifest_digest,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILES = sorted((ROOT / "site_profiles").glob("*.json"))


class SiteManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Hostile mutations use the intentionally small fixture so adding
        # capabilities to the canonical Base2 profile cannot weaken negatives.
        cls.base = load_manifest(ROOT / "site_profiles" / "ember-studio.json")

    def rejected(self, mutation, message):
        payload = copy.deepcopy(self.base)
        mutation(payload)
        with self.assertRaisesRegex(ManifestError, message):
            validate_manifest(payload)

    def test_profiles_validate_and_digest_differently(self):
        self.assertGreaterEqual(len(PROFILES), 3)
        payloads = [load_manifest(path) for path in PROFILES]
        digests = [manifest_digest(payload) for payload in payloads]
        self.assertEqual(len(PROFILES), len(set(digests)))
        self.assertNotEqual(payloads[0]["brand"], payloads[1]["brand"])
        self.assertNotEqual(payloads[0]["modules"], payloads[1]["modules"])

    def test_schema_and_loader_reject_unknown_or_missing_fields(self):
        self.rejected(lambda item: item.update({"unexpected": True}), "fields differ")
        self.rejected(lambda item: item.pop("brand"), "fields differ")
        schema = json.loads(
            (
                ROOT / "specs/093-base2-foundation-hardening/contracts/site-manifest.schema.json"
            ).read_text()
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(self.base) - {"legalName"})

    def test_domain_matrix_rejects_duplicate_or_noncanonical_scope(self):
        self.rejected(
            lambda item: item["domains"].append(copy.deepcopy(item["domains"][0])), "duplicate"
        )
        self.rejected(lambda item: item["domains"][0].update(kind="preview"), "exactly one")
        self.rejected(
            lambda item: item["domains"][0].update(host="https://evil.example/x"), "canonical"
        )
        self.rejected(lambda item: item["domains"][0].update(host="Mixed.example"), "canonical")

    def test_locale_navigation_and_url_matrix_fails_closed(self):
        self.rejected(lambda item: item.update(defaultLocale="es"), "defaultLocale")
        self.rejected(lambda item: item["locales"].append(item["locales"][0]), "locales")
        self.rejected(lambda item: item["locales"].append("en_us"), "locales")
        self.rejected(
            lambda item: item["navigation"][0].update(path="//evil.example"), "safe local"
        )
        self.rejected(lambda item: item["navigation"][0].update(path="/../admin"), "safe local")
        self.rejected(lambda item: item["navigation"][0].update(module="commerce"), "absent")
        self.rejected(
            lambda item: item["brand"].update(logo="https://evil.example/a.svg"), "safe local"
        )

    def test_module_compatibility_and_capability_matrix_fails_closed(self):
        self.rejected(lambda item: item["modules"][0].update(version="99.0.0"), "unsupported")
        self.rejected(lambda item: item["modules"][0].update(id="unknown"), "catalog")
        self.rejected(
            lambda item: item["modules"].append(copy.deepcopy(item["modules"][0])), "duplicated"
        )
        self.rejected(lambda item: item.update(search={"enabled": True}), "search module")
        self.rejected(
            lambda item: item["modules"][0].update(configRef="vault://raw/secret"), "configRef"
        )

    def test_raw_secret_keys_and_values_are_rejected(self):
        self.rejected(
            lambda item: item["brand"].update(apiToken="ghp_" + "x" * 30), "secret-bearing"
        )
        self.rejected(lambda item: item["brand"].update(voice="Bearer " + "x" * 32), "raw secret")

    def test_python_and_node_consumers_agree_on_golden_profiles(self):
        for path in PROFILES:
            payload = load_manifest(path)
            completed = subprocess.run(
                ["node", "scripts/site-manifest.js", str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(payload["siteId"], receipt["siteId"])
            self.assertEqual(manifest_digest(payload), receipt["digest"])

    def test_digest_is_canonical_and_input_is_not_mutated(self):
        before = copy.deepcopy(self.base)
        first = manifest_digest(self.base)
        reordered = {key: self.base[key] for key in reversed(self.base)}
        self.assertEqual(first, manifest_digest(reordered))
        self.assertEqual(before, self.base)

    def test_loader_rejects_symlink_world_writable_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "manifest.json"
            source.write_text(json.dumps(self.base), encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(ManifestError, "real file"):
                load_manifest(link)
            source.chmod(0o606)
            with self.assertRaisesRegex(ManifestError, "world-writable"):
                load_manifest(source)
            source.chmod(0o600)
            source.write_bytes(b" " * 1_000_001)
            with self.assertRaisesRegex(ManifestError, "size limit"):
                load_manifest(source)

    def test_generated_profiles_are_current_and_runtime_selection_fails_closed(self):
        expected = generate(check=True)
        for profile_id, digest in expected.items():
            payload, actual = api_runtime.load_runtime_manifest(profile_id)
            self.assertEqual(profile_id, payload["siteId"])
            self.assertEqual(digest, actual)
        with self.assertRaisesRegex(RuntimeError, "allowed generated profile"):
            api_runtime.load_runtime_manifest("../../escape")

    def test_runtime_rejects_tampered_generated_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source in (ROOT / "api" / "site_profiles").glob("*.json"):
                (root / source.name).write_bytes(source.read_bytes())
            payload = json.loads((root / "ember-studio.json").read_text(encoding="utf-8"))
            payload["name"] = "Tampered"
            (root / "ember-studio.json").write_text(json.dumps(payload), encoding="utf-8")
            with (
                mock.patch.object(api_runtime, "ROOT", root),
                self.assertRaisesRegex(RuntimeError, "integrity verification"),
            ):
                api_runtime.load_runtime_manifest("ember-studio")

    def test_api_and_django_consumers_select_same_profile_digest(self):
        expected = manifest_digest(load_manifest(ROOT / "site_profiles" / "northstar-library.json"))
        environment = {**os.environ, "SITE_PROFILE": "northstar-library"}
        api = subprocess.run(
            [
                str(ROOT / ".venv-api" / "bin" / "python"),
                "-c",
                "from api.settings import settings; print(settings.SITE_MANIFEST_DIGEST)",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        django = subprocess.run(
            [
                str(ROOT / ".venv-django" / "bin" / "python"),
                "-c",
                "from project.settings.base import SITE_MANIFEST_DIGEST; print(SITE_MANIFEST_DIGEST)",
            ],
            cwd=ROOT / "django",
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, api.returncode, api.stderr)
        self.assertEqual(0, django.returncode, django.stderr)
        self.assertEqual(expected, api.stdout.strip())
        self.assertEqual(expected, django.stdout.strip())


if __name__ == "__main__":
    unittest.main()
