import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/python/content_workspace_presets.py"
PRESETS = ROOT / "modules/content-workspace/presets.json"


class ContentWorkspacePresetCompilerTests(unittest.TestCase):
    def compile(self, source=PRESETS):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--presets", str(source)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return result

    def test_all_eight_presets_compile_deterministically_to_closed_definitions(self):
        first = self.compile()
        second = self.compile()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        payload = json.loads(first.stdout)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(len(payload["definitions"]), 8)
        for preset_id, definition in payload["definitions"].items():
            self.assertEqual(definition["typeKey"], preset_id)
            self.assertEqual(definition["presetVersion"], 1)
            self.assertTrue(definition["fields"])
            self.assertEqual(
                len({field["fieldKey"] for field in definition["fields"]}),
                len(definition["fields"]),
            )
            self.assertEqual(definition["workflow"]["initialState"], "draft")

    def test_unknown_field_and_executable_manifest_keys_fail_closed(self):
        for payload in (
            {"schemaVersion": 1, "presets": {"article": {"version": 1, "fields": ["unknown"]}}},
            {
                "schemaVersion": 1,
                "presets": {"article": {"version": 1, "fields": ["title"], "command": "rm"}},
            },
        ):
            with tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "presets.json"
                source.write_text(json.dumps(payload), encoding="utf-8")
                result = self.compile(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("preset_manifest_invalid", result.stderr)


if __name__ == "__main__":
    unittest.main()
