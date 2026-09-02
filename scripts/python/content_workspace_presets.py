#!/usr/bin/env python3
"""Compile the closed Feature 104 preset registry into canonical definitions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
ROOT_KEYS = {"schemaVersion", "presets"}
PRESET_KEYS = {"version", "fields"}

FIELD_LIBRARY = {
    "title": ("short_text", True, {"minLength": 1, "maxLength": 240}),
    "slug": ("slug", True, {"minLength": 1, "maxLength": 160}),
    "summary": ("long_text", False, {"maxLength": 1000}),
    "description": ("long_text", False, {"maxLength": 20000}),
    "body": ("rich_text", False, {"maximumDepth": 8}),
    "hero_image": ("image", False, {}),
    "images": ("references", False, {"targetType": "media_asset", "maximumItems": 20}),
    "gallery": ("references", False, {"targetType": "media_asset", "maximumItems": 20}),
    "attachments": ("references", False, {"targetType": "media_asset", "maximumItems": 20}),
    "price": ("decimal", False, {"minimum": 0, "decimalPlaces": 2}),
    "location": ("location", False, {}),
    "amenities": ("json_object", False, {"maximumDepth": 3}),
    "parent": ("reference", False, {"targetType": "documentation", "maximumDepth": 2}),
    "starts_at": ("datetime", True, {}),
    "ends_at": ("datetime", False, {}),
    "author": ("reference", False, {"targetType": "person", "maximumDepth": 1}),
}

WORKFLOW = {
    "initialState": "draft",
    "states": ["draft", "in_review", "scheduled", "published", "archived", "deleted"],
    "transitions": [
        {"action": "submit_review", "from": ["draft"], "to": "in_review"},
        {"action": "return_draft", "from": ["in_review"], "to": "draft"},
        {"action": "schedule", "from": ["in_review"], "to": "scheduled"},
        {"action": "publish", "from": ["in_review", "scheduled"], "to": "published"},
        {"action": "archive", "from": ["published"], "to": "archived"},
        {"action": "restore", "from": ["archived"], "to": "draft"},
        {"action": "delete", "from": ["draft", "archived"], "to": "deleted"},
    ],
}


def _invalid(message: str) -> ValueError:
    return ValueError(f"preset_manifest_invalid:{message}")


def compile_presets(source: Path) -> dict:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _invalid("unreadable") from exc
    if (
        not isinstance(payload, dict)
        or set(payload) != ROOT_KEYS
        or payload.get("schemaVersion") != 1
        or not isinstance(payload.get("presets"), dict)
        or not 1 <= len(payload["presets"]) <= 32
    ):
        raise _invalid("root")
    definitions = {}
    for preset_id in sorted(payload["presets"]):
        preset = payload["presets"][preset_id]
        if (
            not IDENTIFIER.fullmatch(preset_id)
            or not isinstance(preset, dict)
            or set(preset) != PRESET_KEYS
            or not isinstance(preset.get("version"), int)
            or isinstance(preset.get("version"), bool)
            or preset["version"] < 1
            or not isinstance(preset.get("fields"), list)
            or not 1 <= len(preset["fields"]) <= 64
            or len(set(preset["fields"])) != len(preset["fields"])
        ):
            raise _invalid("preset")
        compiled_fields = []
        for order, field_key in enumerate(preset["fields"]):
            field = FIELD_LIBRARY.get(field_key)
            if field is None:
                raise _invalid("field")
            kind, required, validation = field
            compiled_fields.append(
                {
                    "fieldKey": field_key,
                    "fieldKind": kind,
                    "label": field_key.replace("_", " ").title(),
                    "order": order,
                    "required": required,
                    "validation": validation,
                }
            )
        definitions[preset_id] = {
            "typeKey": preset_id,
            "name": preset_id.replace("_", " ").title(),
            "presetId": preset_id,
            "presetVersion": preset["version"],
            "fields": compiled_fields,
            "workflow": WORKFLOW,
        }
    return {"schemaVersion": 1, "definitions": definitions}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--presets", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        rendered = json.dumps(compile_presets(args.presets), indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
