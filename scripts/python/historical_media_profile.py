"""Proposed source-pinned historical MEDIA classification; no registry migration.

Original packaging completeness did not assert report/diagnostic coverage. This
isolated profile deliberately grants neither byte closure nor native acceptance.
Current native validators and existing quarantine registrations remain unchanged.
"""

import subprocess

from scripts.python import native_archive_evidence as native
from scripts.python import screenshot_archive as a
from scripts.python.typed_archive_support import strict

SOURCES = {
    "scripts/python/visual_matrix_artifacts.py": (
        "a131afa35724ce5a6a20278a87ecf135c5857a56",
        "acc4d18a75a126562e9a68aa7940551b7a94f2d8c91c1cd15e068135761bd466",
    ),
    ".github/workflows/ci-visual-review.yml": (
        "bd57b586b77ae6e4f037109b3a04a162c75a1969",
        "3360fe3d25623e69e1ac397e1f4f69aff208e8ae376955077e959d91577b33af",
    ),
}


def classify(repo, raw, provenance):
    a.verify_source(repo, provenance)
    for path, (blob, sha) in SOURCES.items():
        entry = (
            subprocess.check_output(
                ["git", "ls-tree", provenance["sourceCommit"], "--", path], cwd=repo, timeout=15
            )
            .decode()
            .strip()
        )
        a.require(entry == f"100644 blob {blob}\t{path}", "historical MEDIA source profile")
        body = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=repo, timeout=15)
        a.require(len(body) <= 64 * 1024 and a.digest(body) == sha, "historical MEDIA source bytes")
    data = strict(raw)
    a.require(
        data.get("schemaVersion") == 2
        and data.get("matrix") == "media"
        and type(data.get("complete")) is bool,
        "historical MEDIA inventory profile",
    )
    # Reuse closed shape/source/member/part validation, then apply only this
    # exact historical producer's completeness expression. No original rewrite.
    native.old_inventory(data, provenance, quarantine_contradiction=True)
    a.require(
        any(r["path"] == "source-before.json" for r in data["originalReports"]),
        "historical MEDIA requires source-before",
    )
    packaging_complete = not data["errors"] and all(
        not entry["expectedSupportedTests"] or entry["status"] == "packaged"
        for entry in data["projects"].values()
    )
    a.require(data["complete"] == packaging_complete, "historical MEDIA packaging contradiction")
    gaps = {
        project: dict(
            status=entry["status"],
            missingDiagnostics=entry["missingDiagnostics"],
            minimumCaptureShortfall=entry["minimumCaptureShortfall"],
        )
        for project, entry in data["projects"].items()
        if entry["missingDiagnostics"]
        or entry["minimumCaptureShortfall"]
        or (entry["expectedSupportedTests"] and entry["status"] != "packaged")
    }
    return dict(
        profile="historical-media-packaging-a131afa-bd57b58",
        originalSha256=a.digest(raw),
        originalPackagingComplete=data["complete"],
        originalMissingReports=data["missingReports"],
        originalErrors=data["errors"],
        coverageGaps=gaps,
        nativePartClosure="not-validated-by-classifier",
        dependencyComplete=False,
        runComplete=False,
        acceptance=False,
        migration="proposal-only-original-quarantine-unchanged",
    )
