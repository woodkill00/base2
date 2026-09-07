from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "api/tests/fixtures/media_library_cases.json"


class MediaLibraryFixtureTests(unittest.TestCase):
    def test_fixture_catalog_is_closed_complete_and_contains_no_payloads(self):
        payload = json.loads(FIXTURES.read_text())
        self.assertEqual(1, payload["schemaVersion"])
        self.assertEqual(
            {
                "schemaVersion",
                "safe",
                "hostile",
                "resourceAbuse",
                "authorization",
                "outages",
                "references",
                "accessibility",
            },
            set(payload),
        )
        for category in set(payload) - {"schemaVersion"}:
            self.assertGreaterEqual(len(payload[category]), 4)
            identifiers = [item["id"] for item in payload[category]]
            self.assertEqual(len(identifiers), len(set(identifiers)))
        encoded = FIXTURES.read_bytes()
        self.assertNotIn(b"<script", encoded.lower())
        self.assertNotIn(b"BEGIN PRIVATE KEY", encoded)
        self.assertNotIn(b"secretref:", encoded)


if __name__ == "__main__":
    unittest.main()
