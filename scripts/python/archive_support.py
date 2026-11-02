"""Validate a closed, reviewed diagnostic support set without fetching transfer commits.

The digest catalog is an explicit content/schema allowlist for historical original
records. Extending it requires source review; this is not arbitrary JSON ingestion.
Derived case bindings have their own strict schema and are recomputed below.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

from scripts.python import screenshot_archive as a

CATALOG_PATH = Path(__file__).with_name("archive_support_catalog.json")
BINDING_METHOD = "derived-exact-pinned-Playwright-directory-algorithm-and-original-native-report"
MAX_SUPPORT_BYTES = 16 * 1024 * 1024


def directory(title: str, project: str) -> str:
    prefix = "media-release" if title.startswith("media ") else "operations-release"
    value = prefix + "-" + re.sub(r"[\x00-\x2C\x2E-\x2F\x3A-\x40\x5B-\x60\x7B-\x7F]+", "-", title)
    if len(value) > 60:
        value = value[:26] + "-" + hashlib.sha1(value.encode()).hexdigest()[:5] + "-" + value[-27:]
    return value + "-" + project


def object_path(digest: str, role: str) -> str:
    a.require(bool(a.HEX.fullmatch(digest)), "invalid support digest")
    return f"objects/{digest}.{'md' if role == 'stages.md' else 'json'}"


def load_object(root: Path, descriptor: dict, catalog: dict) -> tuple[Any, str]:
    a.require(set(descriptor) == {"sha256", "bytes", "role", "path"}, "invalid support descriptor")
    digest, role = descriptor["sha256"], descriptor["role"]
    a.require(descriptor["path"] == object_path(digest, role), "noncanonical support path")
    path = a.safe_path(root, descriptor["path"])
    info = path.stat()
    a.require(
        stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_SUPPORT_BYTES,
        "support file size/type bound",
    )
    with path.open("rb") as stream:
        raw = stream.read(MAX_SUPPORT_BYTES + 1)
    a.require(
        0 < len(raw) <= MAX_SUPPORT_BYTES
        and len(raw) == descriptor["bytes"]
        and a.digest(raw) == digest,
        "support content integrity mismatch",
    )
    if role == "derived-case-bindings":
        parsed = json.loads(raw)
        a.require(
            isinstance(parsed, dict)
            and set(parsed) == {"bindings"}
            and isinstance(parsed["bindings"], list)
            and len(parsed["bindings"]) <= 2048,
            "invalid derived bindings schema",
        )
        return parsed, descriptor["path"]
    approved = catalog.get(digest)
    a.require(
        approved is not None and approved["role"] == role and approved["bytes"] == len(raw),
        "unapproved support schema/content/role",
    )
    # Exact digests pin the complete reviewed historical schemas, including nested
    # fields, rather than accepting unknown fields beneath a generic JSON envelope.
    return (raw.decode() if role == "stages.md" else json.loads(raw)), descriptor["path"]


def validate_registry(repo: Path, registry: dict, catalog: dict) -> set[str]:
    a.require(
        set(registry) == {"schemaVersion", "kind", "objects", "runs", "bindingsSha256"}
        and registry["schemaVersion"] == 1
        and registry["kind"] == "diagnostic-support",
        "invalid support registry schema",
    )
    a.require(
        isinstance(registry["objects"], list) and 0 < len(registry["objects"]) <= 128,
        "invalid support object inventory",
    )
    root = repo / "evidence/visual/support"
    objects, paths = {}, set()
    roles = {}
    for descriptor in registry["objects"]:
        value, path = load_object(root, descriptor, catalog)
        digest = descriptor["sha256"]
        a.require(digest not in objects, "duplicate support object")
        objects[digest] = value
        roles[digest] = descriptor["role"]
        paths.add(path)
    binding_hash = registry["bindingsSha256"]
    a.require(roles.get(binding_hash) == "derived-case-bindings", "missing binding record")
    a.require(
        sum(role == "derived-case-bindings" for role in roles.values()) == 1,
        "unexpected binding record",
    )
    a.require(
        isinstance(registry["runs"], list) and 0 < len(registry["runs"]) <= 32,
        "invalid support runs",
    )
    used = {binding_hash}
    seen_runs = set()
    derived = []
    for run in registry["runs"]:
        a.require(set(run) == {"runId", "inventorySha256", "manifests"}, "invalid support run")
        run_id = run["runId"]
        a.require(
            type(run_id) is int and run_id > 0 and run_id not in seen_runs, "duplicate/invalid run"
        )
        seen_runs.add(run_id)
        inv_hash = run["inventorySha256"]
        a.require(roles.get(inv_hash) == "transfer-inventory", "missing original inventory")
        inv = objects[inv_hash]
        a.require(str(inv["runId"]) == str(run_id), "inventory run mismatch")
        used.add(inv_hash)
        reports = inv.get("originalMetadataReceipts", []) + inv.get("provenance", [])
        after = None
        after_hash = None
        for report in reports:
            digest = report.get("sha256") or report["provenanceSha256"]
            member = report["archiveMemberChain"][-1]["member"]
            a.require(
                digest in objects and roles[digest] == member, "missing/wrong-role native proof"
            )
            a.require(
                catalog[digest]["originalPath"]
                == (report.get("objectPath") or report["receiptObjectPath"]),
                "native member binding mismatch",
            )
            value = objects[digest]
            if isinstance(value, dict) and "sourceCommit" in value:
                a.require(
                    value["sourceCommit"] == inv["sourceCommit"]
                    and str(value["runId"]) == str(run_id),
                    "native proof wrong source/run",
                )
                if "sourceTree" in value:
                    a.require(value["sourceTree"] == inv["sourceTree"], "native proof wrong tree")
            if member == "source-after.json":
                after, after_hash = value, digest
            used.add(digest)
        native = {}
        if after is not None:
            a.require(after["tests"] == inv["nativeTests"], "native results disagree")
            for row in after["tests"]:
                key = directory(row["title"], row["project"])
                a.require(key not in native, "ambiguous native case mapping")
                native[key] = row
            current = {
                r["path"].removeprefix("test-results/"): r["sha256"]
                for r in after["currentCaptures"]
            }
            matched = {
                row["caseDirectory"]
                for row in inv["images"]
                if current.get(row["archiveMemberChain"][-1]["member"].removeprefix("members/"))
                == row["sha256"]
            }
            a.require(
                {row["caseDirectory"] for row in inv["images"]} <= matched,
                "native directory lacks original capture/hash proof",
            )
        image_groups: dict[int, list[dict]] = {}
        for image in inv["images"]:
            image_groups.setdefault(image["artifactId"], []).append(image)
        a.require(isinstance(run["manifests"], list), "invalid manifest bindings")
        seen_artifacts = set()
        for entry in run["manifests"]:
            a.require(
                set(entry) == {"path", "sha256"}
                and bool(re.fullmatch(r"runs/[0-9]+-[0-9]+-[0-9]+-[0-9]+\.json", entry["path"])),
                "invalid support manifest path",
            )
            raw = a.safe_path(repo / "evidence/visual", entry["path"]).read_bytes()
            a.require(a.digest(raw) == entry["sha256"], "support manifest hash mismatch")
            manifest = json.loads(raw)
            a.validate_manifest(manifest)
            a.require(
                manifest["runId"] == run_id
                and manifest["sourceCommit"] == inv["sourceCommit"]
                and manifest["sourceTree"] == inv["sourceTree"]
                and manifest["requestedHead"] == inv.get("requestedHead", inv["sourceCommit"]),
                "support manifest wrong source/run",
            )
            expected_outcome = (
                "failed"
                if (after is not None and after["nativeOutcome"] == "failure")
                or any(outcome == "failure" for outcome in inv.get("nativeOutcomes", {}).values())
                else "passed"
            )
            a.require(
                manifest["originalOutcome"] == expected_outcome, "original run outcome mismatch"
            )
            artifact = manifest["artifactId"]
            a.require(
                artifact in image_groups and artifact not in seen_artifacts,
                "unexpected/duplicate artifact",
            )
            seen_artifacts.add(artifact)
            originals = {r["archiveMemberChain"][-1]["member"]: r for r in image_groups[artifact]}
            a.require(
                len(originals) == len(image_groups[artifact]) == len(manifest["captures"]),
                "capture inventory mismatch",
            )
            geometry = [
                row
                for row in inv.get("strictGeometryReceipts", [])
                if row["artifactId"] == artifact
            ]
            a.require(len(geometry) == len(manifest["observations"]), "geometry inventory mismatch")
            by_member = {row["archiveMemberChain"][-1]["member"]: row for row in geometry}
            for observation in manifest["observations"]:
                a.require(observation["member"] in by_member, "unregistered geometry member")
                row = by_member.pop(observation["member"])
                links = [
                    dict(
                        member=link["member"],
                        sha256=row["sha256"]
                        if i == len(row["archiveMemberChain"]) - 1
                        else link.get("sha256"),
                        hashBasis="externally-verified-original-member"
                        if i == len(row["archiveMemberChain"]) - 1 or link.get("sha256")
                        else "unavailable-in-retained-inventory",
                    )
                    for i, link in enumerate(row["archiveMemberChain"])
                ]
                projects = {
                    image.get("project")
                    for image in image_groups[artifact]
                    if Path(image["archiveMemberChain"][-1]["member"]).parent
                    == Path(observation["member"]).parent
                }
                a.require(
                    observation["sha256"] == row["sha256"]
                    and observation["bytes"] == row["sizeBytes"]
                    and observation["schemaVersion"] == row["schemaVersion"]
                    and observation["archiveChain"] == links
                    and projects == {observation["project"]},
                    "geometry provenance mismatch",
                )
            seen_members = set()
            for capture in manifest["captures"]:
                member = capture["member"]
                a.require(
                    member in originals and member not in seen_members, "unregistered capture"
                )
                seen_members.add(member)
                image = originals[member]
                a.require(
                    capture["sha256"] == image["sha256"]
                    and capture["bytes"] == image["sizeBytes"]
                    and capture["dimensions"]
                    == [image["pixels"]["width"], image["pixels"]["height"]]
                    and manifest["archiveSha256"] == image["artifactZipSha256"],
                    "capture provenance mismatch",
                )
                expected_chain = [
                    dict(
                        member=link["member"],
                        sha256=image["sha256"]
                        if i == len(image["archiveMemberChain"]) - 1
                        else link.get("sha256"),
                        hashBasis="externally-verified-original-member"
                        if i == len(image["archiveMemberChain"]) - 1 or link.get("sha256")
                        else "unavailable-in-retained-inventory",
                    )
                    for i, link in enumerate(image["archiveMemberChain"])
                ]
                a.require(
                    capture["archiveChain"] == expected_chain, "archive member chain mismatch"
                )
                case = image["caseDirectory"]
                record = native.get(case)
                if record is None:
                    a.require(
                        capture["originalOutcome"] == "unknown"
                        and capture["identityBasis"] == "archive-directory"
                        and capture["test"] == image["caseDirectory"]
                        and capture["project"] == image.get("project", "unknown-project"),
                        "unknown outcome was promoted",
                    )
                else:
                    a.require(
                        record["attemptStatuses"] == [capture["originalOutcome"]]
                        and record["project"] == capture["project"]
                        and record["title"] == capture["test"],
                        "native outcome mismatch",
                    )
                    derived.append(
                        dict(
                            runId=str(run_id),
                            artifactId=artifact,
                            caseDirectory=case,
                            project=record["project"],
                            title=record["title"],
                            attemptStatuses=record["attemptStatuses"],
                            method=BINDING_METHOD,
                            nativeMetadataSHA256=after_hash,
                        )
                    )
        a.require(seen_artifacts == set(image_groups), "missing artifact manifest")
    a.require(used == set(objects), "unregistered/unbound support object")
    actual = objects[binding_hash]["bindings"]
    a.require(
        sorted(a.canonical(x) for x in actual) == sorted(a.canonical(x) for x in derived),
        "derived native bindings mismatch",
    )
    return paths


def validate_support(repo: Path) -> None:
    root = repo / "evidence/visual/support"
    catalog = json.loads(CATALOG_PATH.read_text())
    known_runs = {
        int(Path(row["originalPath"]).name.split("-", 1)[0])
        for row in catalog.values()
        if row["role"] == "transfer-inventory"
    }
    required_runs = {
        run for run in known_runs if any((repo / "evidence/visual/runs").glob(f"{run}-*.json"))
    }
    if not root.exists():
        a.require(not required_runs, "missing required support registry")
        return
    a.safe_path(repo / "evidence/visual", "support")
    registered = set()
    covered_runs: set[int] = set()
    for path in sorted((root / "registries").glob("*.json")):
        raw = a.safe_path(root, str(path.relative_to(root))).read_bytes()
        a.require(path.stem == a.digest(raw), "support registry hash mismatch")
        registered.add(str(path.relative_to(root)))
        from scripts.python.typed_archive_support import strict
        from scripts.python.typed_archive_support import validate_registry as validate_typed

        data = strict(raw)
        if data.get("schemaVersion") == 5:
            from scripts.python.typed_archive_support import validate_external_registry

            registered.update(validate_external_registry(repo, data))
        elif data.get("schemaVersion") == 3:
            from scripts.python.typed_archive_support import validate_quarantine_registry

            registered.update(validate_quarantine_registry(repo, data))
        elif data.get("schemaVersion") == 2:
            registered.update(validate_typed(repo, data))
        else:
            registered.update(validate_registry(repo, data, catalog))
            covered_runs.update(run["runId"] for run in data["runs"])
    a.require(required_runs <= covered_runs, "missing required support run")
    found = set()
    for path in root.rglob("*"):
        a.require(not path.is_symlink(), "support symlink rejected")
        if path.is_file():
            found.add(str(path.relative_to(root)))
    a.require(found == registered, "unregistered or missing support file")
