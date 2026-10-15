#!/usr/bin/env python3
"""Renew unchanged media references only after a clean-source comparison run.

This cannot approve changed baselines or a redesign. Those need separate review.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = "specs/105-universal-media-library/visual-review.json"
SNAPSHOTS = "react-app/e2e/media/media-release.spec.ts-snapshots"


def validate_results(report: dict) -> None:
    stats = report.get("stats", {})
    if report.get("errors") or any(
        stats.get(key) != expected
        for key, expected in {"expected": 24, "skipped": 12, "unexpected": 0, "flaky": 0}.items()
    ):
        raise ValueError("media_review_requires_complete_nonflaky_matrix")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def clean_source() -> str:
    if git("status", "--porcelain"):
        raise ValueError("media_review_requires_clean_committed_source")
    return git("rev-parse", "HEAD")


def renew() -> None:
    source = clean_source()
    previous = json.loads((ROOT / REVIEW).read_text())
    # Renewal is restricted to the exact previously reviewed image set.
    if git("diff", "--name-only", previous["sourceCommit"], source, "--", SNAPSHOTS):
        raise ValueError("changed_media_references_require_separate_review")
    members = sorted(path.name for path in (ROOT / SNAPSHOTS).glob("*.png"))
    if members != previous["screenshots"] or len(members) != 24:
        raise ValueError("media_reference_inventory_changed")
    result = subprocess.run(
        ["npm", "exec", "--", "playwright", "test",
         "--config=playwright.media-release.config.mjs", "--reporter=json"],
        cwd=ROOT / "react-app", text=True, capture_output=True, timeout=300,
    )
    evidence = ROOT / ".artifacts" / "media-review-renewal" / uuid.uuid4().hex
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "runner.json").write_text(result.stdout)
    (evidence / "runner.stderr.log").write_text(result.stderr)
    if result.returncode:
        raise ValueError("media_comparison_failed_see_private_evidence")
    validate_results(json.loads(result.stdout))
    if clean_source() != source:
        raise ValueError("media_source_changed_during_review")
    previous["sourceCommit"] = source
    (ROOT / REVIEW).write_text(json.dumps(previous, indent=2) + "\n")
    print("media_review_renewed:24_passed:12_intentional_exclusions:unchanged_references")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-reviewed-no-design-change", action="store_true", required=True)
    parser.parse_args()
    renew()


if __name__ == "__main__":
    main()
