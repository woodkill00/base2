"""Package bounded native diagnostics without changing outcomes or references."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

PNG_BUDGET = 28 * 1024 * 1024
ZIP_BUDGET = 30 * 1024 * 1024
METADATA_BUDGET = 2 * 1024 * 1024
PNG_NAME = re.compile(
    r"(?:current-[a-zA-Z0-9_-]+|[a-zA-Z0-9_-]+-(?:actual|expected|diff|post-assert)"
    r"|test-failed-[0-9]+)\.png"
)
REPORTS = ("source-before.json", "source-after.json", "operations-visual-runner.json", "stages.md")


def safe(path: Path) -> None:
    if ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("traversal or symlink rejected")


def read(path: Path, limit: int) -> bytes:
    safe(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("non-regular or oversized evidence")
    return path.read_bytes()


def archive(path: Path, members: dict[str, bytes]) -> None:
    # Inputs have bounded aggregate size; ZIP overhead is checked before exposure.
    temporary = path.with_suffix(".partial")
    with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_STORED) as z:
        for name, raw in members.items():
            z.writestr(name, raw)
    if temporary.stat().st_size > ZIP_BUDGET:
        temporary.unlink()
        raise ValueError("ZIP exceeds transfer budget")
    temporary.rename(path)


def stage(source: Path, output: Path) -> dict:
    safe(source)
    safe(output)
    if output.exists():
        raise ValueError("output must be fresh")
    before_raw = read(source / "source-before.json", METADATA_BUDGET)
    before = json.loads(before_raw)
    projects = sorted({t["project"] for t in before["expectedTests"]})
    if not 1 <= len(projects) <= 14 or any(
        not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", p) for p in projects
    ):
        raise ValueError("invalid declared projects")
    if before.get("matrix") not in {"operations", "media"}:
        raise ValueError("invalid native matrix")
    output.mkdir(parents=True)
    inventory: dict[str, Any] = {
        "schemaVersion": 1,
        "sourceCommit": before["sourceCommit"], "sourceTree": before["sourceTree"],
        "runId": before["runId"], "attempt": before["attempt"], "matrix": before["matrix"],
        "scope": "Diagnostic packaging only; empty/missing captures are incomplete, not acceptance.",
        "originalReports": [], "missingReports": [], "projects": {}, "errors": [],
    }
    reports: dict[str, bytes] = {}
    for name in REPORTS:
        path = source / name
        if not path.exists() and not path.is_symlink():
            inventory["missingReports"].append(name)
            continue
        try:
            raw = read(path, METADATA_BUDGET)
            if sum(map(len, reports.values())) + len(raw) > METADATA_BUDGET:
                raise ValueError("metadata aggregate exceeds budget")
            reports[name] = raw
            inventory["originalReports"].append({
                "path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()
            })
        except ValueError as exc:
            inventory["errors"].append(f"{name}: {exc}")
    results = source / "test-results"
    grouped: dict[str, list[Path]] = {p: [] for p in projects}
    try:
        safe(results)
        if results.exists():
            for case in sorted(results.iterdir()):
                safe(case)
                if not case.is_dir():
                    continue
                matches = [p for p in projects if case.name.endswith("-" + p)]
                if len(matches) != 1:
                    # Unknown directories with PNGs are visible, never guessed.
                    if any(case.glob("*.png")):
                        raise ValueError("PNG directory has no unique declared project")
                    continue
                for path in sorted(case.iterdir()):
                    safe(path)
                    if path.suffix == ".png":
                        if not PNG_NAME.fullmatch(path.name):
                            raise ValueError("unrecognized PNG capture name")
                        grouped[matches[0]].append(path)
    except ValueError as exc:
        inventory["errors"].append(str(exc))
        grouped = {p: [] for p in projects}
    for project, paths in grouped.items():
        supported = [t for t in before["expectedTests"]
                     if t["project"] == project and t.get("expectedStatus") == "passed"]
        entry: dict[str, Any] = {
            "status": "incomplete", "captures": [], "expectedSupportedTests": supported,
            "currentCaptureCount": 0, "minimumCaptureShortfall": len(supported),
            "captureCoverage": "incomplete",
        }
        inventory["projects"][project] = entry
        try:
            if len(paths) > 256 or sum(p.stat().st_size for p in paths) > PNG_BUDGET:
                raise ValueError("project PNG budget exceeded")
            members = {}
            for path in paths:
                raw = read(path, PNG_BUDGET)
                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("invalid PNG signature")
                name = path.relative_to(results).as_posix()
                members[name] = raw
                entry["captures"].append({
                    "path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()
                })
            if members:
                archive(output / f"{project}.zip", members)
                entry["status"] = "packaged"
                current = sum(Path(name).name.startswith("current-") for name in members)
                entry["currentCaptureCount"] = current
                entry["minimumCaptureShortfall"] = max(0, len(supported) - current)
                # Counts cannot prove per-test association or full visual coverage.
                if current and not entry["minimumCaptureShortfall"]:
                    entry["captureCoverage"] = "requires-review"
        except ValueError as exc:
            entry["status"] = "incomplete"
            entry["reason"] = str(exc)
            inventory["errors"].append(f"{project}: {exc}")
    raw_inventory = (json.dumps(inventory, indent=2) + "\n").encode()
    if len(raw_inventory) > METADATA_BUDGET:
        raise ValueError("inventory exceeds budget")
    reports["inventory.json"] = raw_inventory
    archive(output / "metadata.zip", reports)
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = stage(args.source, args.output)
    print(json.dumps({"projects": len(result["projects"]), "errors": result["errors"],
                      "acceptanceGranted": False}))
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
