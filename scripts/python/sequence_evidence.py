"""Read-only validation of native sequence comparison roles, never approval."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

from scripts.python import continuous_evidence, workspace_ownership

NAME = re.compile(r"sequence-([a-z0-9-]{1,90})\.json")
IMAGE = re.compile(r"sequence-([a-z0-9-]{1,90})-(overview|[0-9]{3})-(actual|expected|diff)\.png")
BUDGET = 256 * 1024
STATUSES = {
    "comparison-error",
    "matched",
    "mismatch",
    "missing-reference",
    "invalid-reference",
    "missing-reference-set",
    "invalid-reference-set",
}


REPOSITORY = Path(__file__).resolve().parents[2]


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=pairs)


def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(canonical(value), ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def approved_images(data):
    """Bind transport expected bytes to the repository's exact reviewed set."""
    path = REPOSITORY / "react-app" / data["referenceManifest"]

    def read(member):
        if (
            any(p.is_symlink() for p in (member, *member.parents))
            or not member.is_file()
            or member.stat().st_size > BUDGET
        ):
            raise ValueError("unsafe reference metadata")
        return member.read_bytes()

    raw = read(path)
    if hashlib.sha256(raw).hexdigest() != data["referenceManifestSha256"]:
        raise ValueError("reference manifest changed")
    manifest = strict_json(raw)
    if (
        set(manifest) != {"schemaVersion", "binding", "review", "images"}
        or manifest["schemaVersion"] != 1
        or manifest["binding"] != data["binding"]
    ):
        raise ValueError("reference binding changed")
    review = manifest["review"]
    if set(review) != {"sourceCommit", "sourceTree", "recordSha256"}:
        raise ValueError("invalid reference review")
    for name in ("sourceCommit", "sourceTree"):
        if not isinstance(review[name], str) or not re.fullmatch("[0-9a-f]{40}", review[name]):
            raise ValueError("invalid review source")
    record_raw = read(path.with_suffix(".review.json"))
    if hashlib.sha256(record_raw).hexdigest() != review["recordSha256"]:
        raise ValueError("review hash changed")
    record = strict_json(record_raw)
    if record != dict(
        schemaVersion=1,
        decision="approved-sequence",
        sourceCommit=review["sourceCommit"],
        sourceTree=review["sourceTree"],
        bindingSha256=canonical_hash(manifest["binding"]),
        imagesSha256=canonical_hash(manifest["images"]),
        limitations="captured neutral state only; unrelated overlays and states excluded",
    ):
        raise ValueError("unapproved sequence review")
    tree = subprocess.check_output(
        ["git", "rev-parse", review["sourceCommit"] + "^{tree}"],
        cwd=REPOSITORY,
        text=True,
        timeout=10,
    ).strip()
    if tree != review["sourceTree"]:
        raise ValueError("review tree mismatch")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", review["sourceCommit"], "HEAD"],
        cwd=REPOSITORY,
        check=True,
        timeout=10,
    )
    names = ["overview"] + [f"{i:03}" for i in range(len(data["binding"]["schedule"]))]
    rows = manifest["images"]
    if not isinstance(rows, list) or len(rows) != len(names):
        raise ValueError("approved sequence inventory changed")
    for label, row in zip(names, rows, strict=True):
        if (
            set(row) != {"name", "sha256"}
            or row["name"] != f"sequence-{data['binding']['state']}-{label}.png"
            or not isinstance(row["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", row["sha256"])
        ):
            raise ValueError("approved image identity")
    return rows


def _validate(
    raw: bytes,
    path: Path,
    commit: str,
    tree: str,
    project: str | None = None,
    run: str | None = None,
    attempt: str | None = None,
) -> dict:
    def need(ok):
        if not ok:
            raise ValueError("invalid sequence comparison evidence")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result)
            result[key] = value
        return result

    need(len(raw) <= BUDGET and bool(NAME.fullmatch(path.name)))
    data = json.loads(raw, object_pairs_hook=unique)
    need(isinstance(data, dict))
    need(
        set(data)
        == {
            "schemaVersion",
            "complete",
            "kind",
            "geometryVersion",
            "sourceCommit",
            "sourceTree",
            "runId",
            "attempt",
            "binding",
            "manifestError",
            "referenceManifest",
            "referenceManifestSha256",
            "overlayScope",
            "results",
        }
    )
    need(
        data["schemaVersion"] == 1
        and data["geometryVersion"] == 1
        and data["kind"] == "sequence-comparison"
    )
    need(type(data["complete"]) is bool)
    need(data["sourceCommit"] == commit and data["sourceTree"] == tree)
    need(run is None or data["runId"] == run)
    need(attempt is None or data["attempt"] == attempt)
    need(
        data["overlayScope"]
        == "neutral-focus; known Skip overlay checked; independent unobscured review required"
    )
    binding = data["binding"]
    need(
        set(binding)
        == {
            "project",
            "test",
            "route",
            "state",
            "target",
            "routeStateHash",
            "environmentHash",
            "fixtureVersion",
            "dependencyHash",
            "geometryVersion",
            "pixelPolicy",
            "schedule",
        }
    )
    need(project is None or binding["project"] == project)
    matched_name = NAME.fullmatch(path.name)
    assert matched_name is not None
    state = matched_name[1]
    if state.startswith('workspace-'):
        scenario = workspace_ownership.scenario_for_case(path.parent.name)
        need(scenario is not None and workspace_ownership.state_registered(path.parent.name, state))
        need(binding['test'] == workspace_ownership.TITLES[scenario])
        need(binding['project'] == workspace_ownership.project_for_case(path.parent.name))
    if state.startswith("named-route-"):
        need(state == "named-route-" + hashlib.sha256((binding["route"] + "\0" + binding["test"]).encode()).hexdigest()[:20])
    need(
        binding["state"] == state
        and binding["geometryVersion"] == 1
        and binding["fixtureVersion"] == "synthetic-v1"
    )
    need(
        all(
            isinstance(binding[k], str) and bool(re.fullmatch("[0-9a-f]{64}", binding[k]))
            for k in ("routeStateHash", "environmentHash", "dependencyHash")
        )
    )
    need(
        binding["pixelPolicy"]
        in ({"maxDiffPixelRatio": v, "threshold": 0.2} for v in (0, 0.001, 0.01, 0.02))
    )
    continuous = path.with_name(f"continuous-{state}.json")
    need(not any(p.is_symlink() for p in (continuous, *continuous.parents)))
    need(continuous.is_file() and continuous.stat().st_size <= continuous_evidence.BUDGET)
    native = continuous_evidence.validate(
        continuous.read_bytes(), continuous, commit, tree, project, run, attempt
    )
    need(native["schemaVersion"] == 2 and native["complete"])
    need(all(binding[k] == native[k] for k in ("state", "project", "test", "route", "target")))
    schedule = binding["schedule"]
    need(isinstance(schedule, list) and len(schedule) == len(native["segments"]))
    keys = {
        "offset",
        "max",
        "height",
        "inset",
        "scale",
        "viewport",
        "rect",
        "extent",
        "start",
        "end",
        "next",
    }
    for row, segment in zip(schedule, native["segments"], strict=True):
        need(set(row) == keys)
        # Native receipt validator independently derives start/end/extent from CSS geometry.
        need(all(row[k] == segment[k] for k in keys - {"next"}))
        need(row["next"] == min(row["max"], row["offset"] + (row["end"] - row["start"]) * 0.75))
    need(
        isinstance(data["referenceManifest"], str)
        and bool(
            re.fullmatch(
                r"e2e/(?:media/media-release|operations/operations-release|workspace/workspace-release|layout/volcano-preservation|journeys/public-journeys)\.spec\.ts-snapshots/sequence-[a-z0-9-]+\.json",
                data["referenceManifest"],
            )
        )
    )
    need(
        data["referenceManifestSha256"] is None
        or bool(re.fullmatch("[0-9a-f]{64}", data["referenceManifestSha256"]))
    )
    need(data["manifestError"] in (None, "missing-reference-set", "invalid-reference-set"))
    need(
        data["manifestError"] != "missing-reference-set" or data["referenceManifestSha256"] is None
    )
    labels = ["overview"] + [f"{i:03}" for i in range(len(schedule))]
    results = data["results"]
    need(isinstance(results, list) and len(results) <= len(labels))
    need(not data["complete"] or len(results) == len(labels))
    references = approved_images(data) if data["manifestError"] is None else None
    for i, result in enumerate(results):
        need(set(result) == {"index", "label", "status", "actual", "expected", "diff"})
        need(result["index"] == i and result["label"] == labels[i] and result["status"] in STATUSES)
        need(result["actual"] is not None)
        comparable = result["status"] in ("matched", "mismatch", "comparison-error")
        need(
            not comparable
            or (data["referenceManifestSha256"] is not None and data["manifestError"] is None)
        )
        need((result["expected"] is not None) == comparable)
        need(result["diff"] is None or result["status"] == "mismatch")
        need(not data["manifestError"] or result["status"] == data["manifestError"])
        for role in ("actual", "expected", "diff"):
            image = result[role]
            if image is None:
                continue
            need(set(image) == {"file", "sha256", "bytes", "dimensions"})
            need(image["file"] == f"sequence-{state}-{labels[i]}-{role}.png")
            target = path.parent / image["file"]
            need(not any(p.is_symlink() for p in (target, *target.parents)))
            need(type(image["bytes"]) is int and 24 <= image["bytes"] <= 28 * 1024 * 1024)
            need(target.is_file() and target.stat().st_size == image["bytes"])
            content = target.read_bytes()
            need(
                content.startswith(b"\x89PNG\r\n\x1a\n")
                and hashlib.sha256(content).hexdigest() == image["sha256"]
            )
            dimensions = list(struct.unpack(">II", content[16:24]))
            need(
                dimensions == image["dimensions"]
                and all(0 < n <= 16384 for n in dimensions)
                and dimensions[0] * dimensions[1] <= 16 * 1024 * 1024
            )
            if role == "expected":
                need(references is not None and image["sha256"] == references[i]["sha256"])
            if role == "actual":
                segment = native["segments"][max(0, i - 1)]
                need(image["sha256"] == segment["sha256"] and image["bytes"] == segment["bytes"])
    return data


def images(data: dict) -> list[dict]:
    return [
        image
        for result in data["results"]
        for role in ("actual", "expected", "diff")
        if (image := result[role]) is not None
    ]


def registered(suite: str, case: str, state: str) -> bool:
    if suite == "media":
        return case.startswith("media-release-") and state in {
            "media-library",
            "media-detail-ready",
            "media-detail-pending",
            "media-detail-deleted",
            "media-detail-restored",
            "media-picker",
        }
    if suite == "operations":
        return case.startswith("operations-release-") and (
            state
            in {
                "operations-cancel",
                "operations-center-empty",
                "operations-center-error",
                "operations-center-partial",
                "operations-center-reauth",
                "operations-center-read-only",
                "operations-center-cancel-confirmation",
            }
            or bool(
                re.fullmatch(r"operations-center-(?:chromium|firefox|webkit)-[a-z0-9-]+", state)
            )
        )
    if suite == "workspace":
        return workspace_ownership.state_registered(case, state) and state != 'current'
    if suite == "volcano":
        return case.startswith("volcano-preservation-") and (state in {"named-route", "volcano-home"} or bool(re.fullmatch(r"named-route-[a-f0-9]{20}", state)))
    if suite == "journeys":
        return (
            case.startswith("public-journeys-public-jou-") and state == "journey-contact-received"
        )
    return False


def validate(raw: bytes, path: Path, commit: str, tree: str, project: str | None = None,
             run: str | None = None, attempt: str | None = None) -> dict:
    """Normalize malformed JSON shapes without swallowing IO or programming failures."""
    try:
        return _validate(raw, path, commit, tree, project, run, attempt)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError("invalid sequence comparison evidence shape") from exc
