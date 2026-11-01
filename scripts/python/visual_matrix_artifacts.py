"""Package bounded native diagnostics without changing outcomes or references."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import zipfile
from pathlib import Path
from typing import Any

from scripts.python import continuous_evidence

PNG_BUDGET = 28 * 1024 * 1024
ZIP_BUDGET = 30 * 1024 * 1024
METADATA_BUDGET = 2 * 1024 * 1024
OBSERVATION_BUDGET = 64 * 1024
OBSERVATION_NAME = "media-viewport-observations.json"
MEDIA_CASE = "media-release-media-librar-1b4ce-nsive-and-visually-reviewed-"
MEDIA_TEST = "media library is accessible responsive and visually reviewed"
CONTROL_IDS = {"base2-scroll-ascend", "base2-scroll-descend"}
PNG_NAME = re.compile(
    r"(?:current-[a-zA-Z0-9_-]+|[a-zA-Z0-9_-]+-(?:actual|expected|diff|post-assert)"
    r"|test-failed-[0-9]+)\.png"
)
REPORTS = ("source-before.json", "source-after.json", "operations-visual-runner.json", "stages.md")


def observations(raw: bytes, project: str) -> dict:
    """Accept only synthetic geometry/enums, never DOM text or generic JSON."""
    def require(condition: bool) -> None:
        if not condition:
            raise ValueError("invalid viewport observation schema")

    def unique(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    def number(value: Any) -> bool:
        return type(value) in {int, float} and abs(value) <= 100_000 and math.isfinite(value)

    def rect(value: Any) -> None:
        require(isinstance(value, dict) and set(value) ==
                {"x", "y", "width", "height", "top", "right", "bottom", "left"})
        require(all(number(v) for v in value.values()))
        require(value["width"] >= 0 and value["height"] >= 0)

    data = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(data, dict) and set(data) == {
        "schemaVersion", "fixtureScope", "project", "test", "scope", "viewportObservations"})
    require(type(data["schemaVersion"]) is int and data["schemaVersion"] in (1, 2, 3, 4))
    require(data["fixtureScope"] == "synthetic-project-tests" and data["project"] == project)
    require(data["test"] == MEDIA_TEST)
    require(data["scope"] == "Diagnostic viewport observations; not visual acceptance.")
    rows = data["viewportObservations"]
    require(isinstance(rows, list) and len(rows) == 3)
    for index, row in zip((0, 2, 4), rows, strict=True):
        require(isinstance(row, dict) and set(row) ==
                ({"cardIndex", "scrollY", "viewport", "controls", "targets"}
                 | ({"contentViewport"} if data["schemaVersion"] >= 3 else set())
                 | ({"unobscuredContentViewport"} if data["schemaVersion"] == 4 else set())))
        if data["schemaVersion"] >= 3:
            rect(row["contentViewport"])
        if data["schemaVersion"] == 4:
            rect(row["unobscuredContentViewport"])
            raw_view, visible = row["contentViewport"], row["unobscuredContentViewport"]
            require(raw_view["top"] <= visible["top"] <= visible["bottom"] <= raw_view["bottom"]
                    and visible["left"] == raw_view["left"] and visible["right"] == raw_view["right"])
        require(type(row["cardIndex"]) is int and row["cardIndex"] == index)
        require(number(row["scrollY"]) and row["scrollY"] >= 0)
        require(isinstance(row["viewport"], list) and len(row["viewport"]) == 2
                and all(type(v) is int and 0 < v <= 32768 for v in row["viewport"]))
        require(isinstance(row["controls"], list) and len(row["controls"]) <= (4 if data["schemaVersion"] == 4 else 2))
        ids = []
        for control in row["controls"]:
            require(isinstance(control, dict) and set(control) == {"id", "rect"})
            require(isinstance(control["id"], str) and control["id"] in (CONTROL_IDS | {
                "base2-left-menu-toggle", "base2-right-utility-toggle"} if data["schemaVersion"] == 4 else CONTROL_IDS))
            ids.append(control["id"])
            rect(control["rect"])
        require(len(set(ids)) == len(ids))
        require(isinstance(row["targets"], list) and
                (len(row["targets"]) == 5 if data["schemaVersion"] == 1 else 0 <= len(row["targets"]) <= 25))
        identities = set()
        for target in row["targets"]:
            require(isinstance(target, dict) and set(target) ==
                    ({"kind", "rect", "centerInViewport", "centerUnobstructed", "overlappingControls"}
                     | ({"cardIndex", "targetIndex"} if data["schemaVersion"] >= 2 else set())
                     | ({"centerInUnobscuredContent"} if data["schemaVersion"] == 4 else set())))
            if data["schemaVersion"] == 4:
                require(type(target["centerInUnobscuredContent"]) is bool)
            if data["schemaVersion"] >= 2:
                require(type(target["cardIndex"]) is int and 0 <= target["cardIndex"] < 5)
                require(type(target["targetIndex"]) is int and 0 <= target["targetIndex"] < 5)
                identity = (target["cardIndex"], target["targetIndex"])
                require(identity not in identities)
                identities.add(identity)
            require(target["kind"] in ("filename", "metadata", "status", "action"))
            rect(target["rect"])
            require(type(target["centerInViewport"]) is bool
                    and type(target["centerUnobstructed"]) is bool)
            overlaps = target["overlappingControls"]
            require(isinstance(overlaps, list) and len(overlaps) <= (4 if data["schemaVersion"] == 4 else 2)
                    and all(isinstance(v, str) and v in ids for v in overlaps)
                    and len(set(overlaps)) == len(overlaps))
    return data


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
    safe(path)
    if path.exists():
        raise ValueError("duplicate archive destination")
    temporary = path.with_suffix(".partial")
    with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_STORED) as z:
        for name, raw in members.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            z.writestr(info, raw)
    if temporary.stat().st_size > ZIP_BUDGET:
        temporary.unlink()
        raise ValueError("ZIP exceeds transfer budget")
    temporary.rename(path)


def project_archives(output: Path, project: str, members: dict[str, Path], entry: dict) -> None:
    """Split whole validated members deterministically; never concatenate for upload."""
    groups: list[list[str]] = []
    current: list[str] = []
    size = 0
    for name, path in sorted(members.items()):
        member_size = path.stat().st_size
        if member_size > PNG_BUDGET:
            raise ValueError("single member exceeds payload budget")
        if current and size + member_size > PNG_BUDGET:
            groups.append(current)
            current, size = [], 0
        current.append(name)
        size += member_size
    if current:
        groups.append(current)
    identities = {item["path"]: item for item in entry["captures"] + entry["diagnostics"]}
    for index, names in enumerate(groups, 1):
        filename = f"{project}.zip" if len(groups) == 1 else f"{project}-part-{index:03d}.zip"
        payload = {}
        for name in names:
            raw = read(members[name], PNG_BUDGET)
            if (len(raw) != identities[name]["bytes"] or
                    hashlib.sha256(raw).hexdigest() != identities[name]["sha256"]):
                raise ValueError("evidence changed during packaging")
            payload[name] = raw
        path = output / filename
        archive(path, payload)
        entry["parts"].append({"path": filename, "bytes": path.stat().st_size,
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                               "members": names})
        for name in names:
            identities[name]["archive"] = filename


def upload_action(output: Path, destination: Path, inventory: dict) -> None:
    """Emit data-only pinned upload steps, never shell or native report content."""
    safe(output)
    safe(destination)
    if output != Path(os.environ.get("VISUAL_OUTPUT", "")) / "bounded":
        raise ValueError("upload output must match workflow evidence directory")
    if destination.exists() or inventory["errors"]:
        raise ValueError("upload action requires fresh destination and complete packaging")
    parts = [part for entry in inventory["projects"].values() for part in entry["parts"]]
    if not parts or len(parts) > 480:
        raise ValueError("upload part count outside bounded action budget")
    names = [part["path"] for part in parts]
    if len(set(names)) != len(names):
        raise ValueError("duplicate upload part")
    # Fixed workflow path; no caller/native value becomes an expression or command.
    if destination != Path('.artifacts/visual-upload-action'):
        raise ValueError("unexpected upload action destination")
    steps = []
    for part in parts:
        name = part["path"]
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}(?:-part-[0-9]{3})?\.zip", name):
            raise ValueError("invalid upload part name")
        raw = read(output / name, ZIP_BUDGET)
        if len(raw) != part["bytes"] or hashlib.sha256(raw).hexdigest() != part["sha256"]:
            raise ValueError("upload part identity mismatch")
        steps.append({"name": "Retain " + name, "if": "always()",
                      "uses": "actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f",
                      "with": {"name": "visual-png-" + name[:-4] +
                               "-${{ env.REVIEW_LABEL }}-${{ github.run_id }}-${{ github.run_attempt }}",
                               "path": "${{ env.VISUAL_OUTPUT }}/bounded/" + name,
                               "if-no-files-found": "error", "retention-days": 7,
                               "compression-level": 0}})
    destination.mkdir(parents=True)
    (destination / "action.yml").write_text(json.dumps({
        "name": "Upload bounded visual parts", "description": "Exact diagnostic ZIP parts only",
        "runs": {"using": "composite", "steps": steps}}, indent=2) + "\n")


def stage(source: Path, output: Path) -> dict:
    safe(source)
    safe(output)
    if output.exists():
        raise ValueError("output must be fresh")
    if output.is_relative_to(source / "test-results") or source.is_relative_to(output):
        raise ValueError("output overlaps native input collection")
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
        "schemaVersion": 2,
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
    diagnostics: dict[str, list[Path]] = {p: [] for p in projects}
    sweeps: dict[str, list[Path]] = {p: [] for p in projects}
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
                    elif continuous_evidence.NAME.fullmatch(path.name):
                        sweeps[matches[0]].append(path)
                    elif path.name == OBSERVATION_NAME:
                        project = matches[0]
                        declared = any(t["project"] == project and t.get("title") == MEDIA_TEST
                                       and t.get("expectedStatus") == "passed"
                                       for t in before["expectedTests"])
                        if before["matrix"] != "media" or case.name != MEDIA_CASE + project or not declared:
                            raise ValueError("observation outside declared media library case")
                        diagnostics[project].append(path)
    except ValueError as exc:
        inventory["errors"].append(str(exc))
        grouped = {p: [] for p in projects}
        diagnostics = {p: [] for p in projects}
    for project, paths in grouped.items():
        supported = [t for t in before["expectedTests"]
                     if t["project"] == project and t.get("expectedStatus") == "passed"]
        entry: dict[str, Any] = {
            "status": "incomplete", "captures": [], "expectedSupportedTests": supported,
            "currentCaptureCount": 0, "minimumCaptureShortfall": len(supported),
            "captureCoverage": "incomplete",
            "diagnostics": [], "parts": [],
            "missingDiagnostics": [OBSERVATION_NAME] if before["matrix"] == "media" else [],
        }
        inventory["projects"][project] = entry
        try:
            continuous_count = sum(bool(continuous_evidence.FRAME.fullmatch(p.name)) for p in paths)
            if continuous_count > 1024 or len(sweeps[project]) > 16 or len(paths) - continuous_count > 256:
                raise ValueError("project capture count exceeded")
            members = {}
            for path in paths:
                raw = read(path, PNG_BUDGET)
                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("invalid PNG signature")
                name = path.relative_to(results).as_posix()
                members[name] = path
                entry["captures"].append({
                    "path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()
                })
            bound_frames = set()
            for receipt in sweeps[project]:
                raw = read(receipt, continuous_evidence.BUDGET)
                data = continuous_evidence.validate(raw, receipt, before['sourceCommit'], before['sourceTree'], project, str(before['runId']), str(before['attempt']))
                if data['test'] not in {t['title'] for t in before['expectedTests'] if t['project'] == project}:
                    raise ValueError('continuous receipt outside declared test')
                for row in data['segments']:
                    name = (receipt.parent / row['file']).relative_to(results).as_posix()
                    if name not in members or name in bound_frames:
                        raise ValueError('missing or duplicate continuous frame binding')
                    bound_frames.add(name)
                name = receipt.relative_to(results).as_posix()
                members[name] = receipt
                entry['diagnostics'].append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                                             'complete': data['complete'], 'kind': 'continuous-viewports'})
            if {name for name in members if continuous_evidence.FRAME.fullmatch(Path(name).name)} != bound_frames:
                raise ValueError('unbound continuous frame')
            if len(diagnostics[project]) > 1:
                raise ValueError("duplicate project observation file")
            for path in diagnostics[project]:
                raw = read(path, OBSERVATION_BUDGET)
                data = observations(raw, project)
                for row in data["viewportObservations"]:
                    capture = path.parent / f"current-media-library-viewport-{row['cardIndex']}.png"
                    if capture.relative_to(results).as_posix() not in members:
                        raise ValueError("observation missing corresponding viewport PNG")
                name = path.relative_to(results).as_posix()
                members[name] = path
                entry["diagnostics"].append({
                    "path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()
                })
                entry["missingDiagnostics"] = []
            if members:
                project_archives(output, project, members, entry)
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
    parser.add_argument("--upload-action", action="store_true")
    args = parser.parse_args()
    result = stage(args.source, args.output)
    if args.upload_action and not result["errors"]:
        upload_action(args.output, Path('.artifacts/visual-upload-action'), result)
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
            stream.write("upload_ready=true\n")
    print(json.dumps({"projects": len(result["projects"]), "errors": result["errors"],
                      "acceptanceGranted": False}))
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
