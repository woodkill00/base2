from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "shared/config/design-system-v1.json"
SCHEMA = ROOT / "shared/schemas/design-system-v1.schema.json"
TOKENS = ROOT / "react-app/src/styles/tokens.css"


class VisualContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_and_schema_are_strict_and_versioned(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(1, self.contract["schemaVersion"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(self.contract))
        jsonschema.Draft202012Validator(schema).validate(self.contract)

    def test_required_semantic_token_families_and_themes_are_complete(self):
        self.assertEqual(
            {"color", "space", "radius", "motion", "typography", "breakpoint"},
            set(self.contract["tokens"]),
        )
        self.assertEqual({"volcanic", "obsidian", "polar"}, set(self.contract["themes"]))
        required_colors = {
            "canvas",
            "surface",
            "surfaceElevated",
            "text",
            "textMuted",
            "border",
            "accent",
            "focus",
            "danger",
            "success",
        }
        for theme in self.contract["themes"].values():
            self.assertEqual(required_colors, set(theme["color"]))
            self.assertIn(theme["colorScheme"], {"light", "dark"})

    def test_css_exposes_every_declared_token_without_raw_component_colors(self):
        css = TOKENS.read_text(encoding="utf-8")
        declared = set(re.findall(r"(--[a-z0-9-]+)\s*:", css))
        expected = set(self.contract["cssVariables"])
        self.assertTrue(expected <= declared, sorted(expected - declared))
        components = (ROOT / "react-app/src/components/glass").glob("*.*sx")
        for path in components:
            source = path.read_text(encoding="utf-8")
            self.assertNotRegex(source, r"#[0-9a-fA-F]{3,8}", path.name)

    def test_component_state_contract_is_total_and_story_backed(self):
        expected = {
            "button": {"default", "hover", "focus-visible", "disabled"},
            "input": {"default", "focus-visible", "error", "disabled"},
            "modal": {"closed", "open", "focus-trapped"},
            "tabs": {"default", "selected", "focus-visible"},
            "navigation": {"desktop", "mobile", "open", "active", "focus-visible"},
        }
        self.assertEqual(
            expected, {key: set(value) for key, value in self.contract["componentStates"].items()}
        )
        stories = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "react-app/src/stories").rglob("*.stories.*")
        )
        for component, states in expected.items():
            for state in states:
                marker = f"contract:{component}:{state}"
                self.assertIn(marker, stories)

    def test_motion_and_breakpoints_are_bounded_and_reduced_motion_is_explicit(self):
        motion = self.contract["tokens"]["motion"]
        self.assertTrue(all(0 <= value <= 500 for value in motion["durationMs"].values()))
        breakpoints = list(self.contract["tokens"]["breakpoint"].values())
        self.assertEqual(breakpoints, sorted(breakpoints))
        css = TOKENS.read_text(encoding="utf-8") + (
            ROOT / "react-app/src/styles/glass.css"
        ).read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", css)


if __name__ == "__main__":
    unittest.main()
