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
RUNNER_RECEIPT = ROOT / "specs/106-production-readiness-program/operations-visual-runner.json"
SOURCES = (
    "react-app/src/pages/OperationsCenter.jsx",
    "react-app/src/services/operations.js",
    "react-app/src/components/glass/AppShell.tsx",
    "react-app/src/components/glass/unified-layout.css",
    "react-app/src/config/layoutPolicy.ts",
    "react-app/src/config/siteRuntime.ts",
    "react-app/src/config/generated/base2-obsidian.json",
    "react-app/src/components/glass/GlassButton.tsx",
    "react-app/src/components/glass/GlassCard.tsx",
    "react-app/src/components/glass/GlassHeader.tsx",
    "react-app/src/components/glass/GlassSidebar.tsx",
    "react-app/src/components/glass/ThemeToggle.tsx",
    "react-app/src/components/Navigation.js",
    "react-app/src/index.css",
    "react-app/src/styles/tokens.css",
    "react-app/src/styles/experience.css",
    "react-app/src/App.css",
    "react-app/src/contexts/ThemeContext.js",
    "react-app/src/services/theme/persistence.ts",
    "react-app/e2e/operations/operations-release.spec.ts",
    "react-app/playwright.operations-release.config.mjs",
    "react-app/e2e/operations/visual-receipt-reporter.mjs",
)
CAPTURE_NAMES = {
    *(
        f"operations-center-chromium-{mode}-chromium-{mode}-linux.png"
        for mode in (
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
            "german",
            "reduced-motion",
        )
    ),
    "operations-center-cancel-confirmation-chromium-desktop-linux.png",
    *(
        f"operations-center-{state}-{project}-linux.png"
        for state in ("empty", "error", "partial", "reauth", "read-only")
        for project in ("chromium-compact", "chromium-desktop", "firefox-desktop", "webkit-desktop")
    ),
    "operations-center-firefox-desktop-firefox-desktop-linux.png",
    "operations-center-webkit-desktop-webkit-desktop-linux.png",
}
PROJECTS = tuple(
    [
        f"chromium-{mode}"
        for mode in (
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
            "german",
            "reduced-motion",
        )
    ]
    + ["firefox-desktop", "webkit-desktop"]
)
STATE_PROJECTS = {"chromium-compact", "chromium-desktop", "firefox-desktop", "webkit-desktop"}
TITLES = {
    "operations center is accessible responsive and visually stable": "operations-primary",
    "operations center shows truthful empty and failure states": "operations-empty-error",
    "operations center exposes stale, reauthentication, and read-only recovery states": "operations-recovery",
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
    capture_names = {path.name for path in screenshots}
    if capture_names != CAPTURE_NAMES:
        raise VisualEvidenceError(
            "visual captures differ: "
            f"missing={sorted(CAPTURE_NAMES - capture_names)} "
            f"extra={sorted(capture_names - CAPTURE_NAMES)}"
        )
    try:
        runner = json.loads(RUNNER_RECEIPT.read_text(encoding="utf-8"))
        unsigned_runner = {key: runner[key] for key in runner if key != "digest"}
        expected_runner_digest = hashlib.sha256(
            json.dumps(unsigned_runner, separators=(",", ":")).encode()
        ).hexdigest()
        rows = runner.get("tests", [])
        expected_pairs = {(project, title) for project in PROJECTS for title in TITLES}
        actual_pairs = {(row.get("project"), row.get("title")) for row in rows}
        receipt_captures = {
            capture.get("name"): capture.get("sha256")
            for row in rows
            for capture in row.get("captures", [])
            if isinstance(capture, dict)
        }
        rows_honest = all(
            row.get("assertionId") == TITLES.get(row.get("title"))
            and row.get("status")
            == (
                "passed"
                if row.get("title") == next(iter(TITLES)) or row.get("project") in STATE_PROJECTS
                else "skipped"
            )
            and bool(row.get("captures")) == (row.get("status") == "passed")
            for row in rows
        )
        if (
            set(runner) != {"schemaVersion", "status", "tests", "digest"}
            or runner["schemaVersion"] != 1
            or runner["status"] != "passed"
            or actual_pairs != expected_pairs
            or len(rows) != len(expected_pairs)
            or not rows_honest
            or set(receipt_captures) != CAPTURE_NAMES
            or any(receipt_captures[path.name] != _sha256(path) for path in screenshots)
            or runner["digest"] != expected_runner_digest
        ):
            raise ValueError("runner receipt did not prove the exact asserted/skipped matrix")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise VisualEvidenceError(f"visual runner receipt invalid: {exc}") from exc
    return {
        "schemaVersion": 1,
        "status": "accepted",
        "sources": {name: _sha256(ROOT / name) for name in SOURCES},
        "screenshots": {
            path.name: {"sha256": _sha256(path), "pixels": _png_size(path)} for path in screenshots
        },
        "runnerReceipt": {"sha256": _sha256(RUNNER_RECEIPT), "digest": runner["digest"]},
        "assertions": {
            "accessibility": "pass",
            "console": "pass",
            "focus": "pass",
            "overflow": "pass",
            "requests": "pass",
            "keyboard": "pass",
            "touchTargets": "pass",
            "reducedMotion": "pass",
            "rtlLocalization": "pass",
            "degradedEvidence": "pass",
            "recentAuthenticationRecovery": "pass",
            "readOnlyBoundary": "pass",
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
