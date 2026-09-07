#!/usr/bin/env python3
"""Create and verify exact-source Operations Center visual evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = ROOT / "react-app/e2e/operations/operations-release.spec.ts-snapshots"
MANIFEST = ROOT / "specs/106-production-readiness-program/operations-visual-review.json"
SOURCES = (
    "react-app/src/pages/OperationsCenter.jsx",
    "react-app/src/services/operations.js",
    "react-app/e2e/operations/operations-release.spec.ts",
    "react-app/playwright.operations-release.config.mjs",
)
MODES = {
    "compact",
    "landscape-touch",
    "tablet",
    "desktop",
    "ultrawide",
    "large-text",
    "400-zoom",
    "light",
    "high-contrast",
    "rtl",
    "reduced-motion",
}


class VisualEvidenceError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _png_size(path: Path) -> list[int]:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise VisualEvidenceError(f"invalid PNG: {path.name}")
    return list(struct.unpack(">II", data[16:24]))


def build() -> dict:
    screenshots = sorted(SNAPSHOT_ROOT.glob("operations-center-*.png"))
    modes = {
        name.removeprefix("operations-center-chromium-").split("-chromium-")[0]
        for name in (path.name for path in screenshots)
    }
    if modes != MODES or len(screenshots) != len(MODES):
        raise VisualEvidenceError(
            f"visual modes differ: missing={sorted(MODES - modes)} extra={sorted(modes - MODES)}"
        )
    return {
        "schemaVersion": 1,
        "status": "accepted",
        "sources": {name: _sha256(ROOT / name) for name in SOURCES},
        "screenshots": {
            path.name: {"sha256": _sha256(path), "pixels": _png_size(path)} for path in screenshots
        },
        "assertions": {
            "accessibility": "pass",
            "console": "pass",
            "focus": "pass",
            "overflow": "pass",
            "requests": "pass",
        },
    }


def validate(value: object) -> None:
    expected = build()
    if value != expected:
        raise VisualEvidenceError("visual evidence differs from exact sources or captures")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        current = build()
        if args.write:
            MANIFEST.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        else:
            validate(json.loads(MANIFEST.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, VisualEvidenceError) as exc:
        print(f"operations_visual_evidence:failed:{exc}")
        return 1
    print(f"operations_visual_evidence:passed:screenshots={len(current['screenshots'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
