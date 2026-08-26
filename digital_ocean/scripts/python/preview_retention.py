#!/usr/bin/env python3
"""Bounded cleanup of old, unapproved preview visual evidence only."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from digital_ocean.scripts.python.preview_inventory import admit_private_root, inventory


class RetentionError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _run_time(run_id: str) -> datetime:
    try:
        return datetime.strptime(run_id.removeprefix("base2-full-"), "%Y%m%d-%H%M%S").replace(
            tzinfo=UTC
        )
    except ValueError as exc:
        raise RetentionError("EVIDENCE_INVALID", "retention run identity is invalid") from exc


def cleanup_visual_evidence(
    state_root: str | os.PathLike[str],
    *,
    apply: bool = False,
    now: datetime | None = None,
    minimum_age_days: int = 14,
    keep_runs: int = 10,
    maximum_files: int = 250,
) -> dict:
    if (
        not 7 <= minimum_age_days <= 365
        or not 1 <= keep_runs <= 100
        or not 1 <= maximum_files <= 500
    ):
        raise RetentionError("EVIDENCE_INVALID", "retention policy is outside fixed bounds")
    root = admit_private_root(state_root)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    leases = inventory(root, now=current)["leases"]
    destroyed = sorted(
        (row for row in leases if row["effectiveState"] == "destroyed"),
        key=lambda row: row["runId"],
        reverse=True,
    )
    candidates: list[Path] = []
    skipped_approved: list[str] = []
    for lease in destroyed[keep_runs:]:
        if _run_time(lease["runId"]) > current - timedelta(days=minimum_age_days):
            continue
        run_root = root / lease["runId"]
        for evidence_root in sorted(run_root.glob("browser*")):
            if evidence_root.is_symlink() or not evidence_root.is_dir():
                continue
            review = evidence_root / "visual-review.json"
            if review.is_file() and not review.is_symlink():
                try:
                    if json.loads(review.read_text(encoding="utf-8")).get("state") == "approved":
                        skipped_approved.append(str(evidence_root.relative_to(root)))
                        continue
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise RetentionError(
                        "EVIDENCE_INVALID", "retention review sidecar is invalid"
                    ) from exc
            for path in sorted(evidence_root.iterdir()):
                if path.is_symlink() or not path.is_file():
                    continue
                if path.suffix.casefold() == ".png" or path.name in {
                    "visual-evidence.json",
                    "visual-evidence.html",
                }:
                    candidates.append(path)
    if len(candidates) > maximum_files:
        raise RetentionError("EVIDENCE_INVALID", "retention candidate count exceeds fixed bound")
    deleted = []
    if apply:
        for path in candidates:
            path.unlink()
            deleted.append(str(path.relative_to(root)))
    return {
        "schemaVersion": 1,
        "ok": True,
        "code": "OK",
        "mode": "apply" if apply else "plan",
        "candidateCount": len(candidates),
        "candidates": [str(path.relative_to(root)) for path in candidates],
        "deleted": deleted,
        "approvedEvidenceSkipped": skipped_approved,
        "providerStateFilesDeleted": 0,
        "approvedBaselinesDeleted": 0,
        "secretValuesEmitted": 0,
    }
