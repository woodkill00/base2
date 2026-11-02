"""Integrity tests for the explicitly reviewed historical support registry."""

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from scripts.python import archive_support as support
from scripts.python import screenshot_archive as archive


@pytest.fixture
def registered(tmp_path):
    source = Path(os.environ.get("ARCHIVE_SUPPORT_TEST_ROOT", Path(__file__).parents[2]))
    root = source / "evidence/visual"
    target = tmp_path / "evidence/visual"
    shutil.copytree(root / "support", target / "support")
    registry_path = next((target / "support/registries").glob("*.json"))
    registry = json.loads(registry_path.read_text())
    for run in registry["runs"]:
        for item in run["manifests"]:
            path = target / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / item["path"], path)
    return tmp_path, registry, json.loads(support.CATALOG_PATH.read_text())


def test_original_support_and_all_case_bindings_validate(registered):
    repo, registry, catalog = registered
    paths = support.validate_registry(repo, registry, catalog)
    assert len(paths) == 25
    support.validate_support(repo)


@pytest.mark.parametrize("mutation", ["tamper", "missing", "unregistered", "symlink"])
def test_stored_support_rejects_invalid_files(registered, mutation):
    repo, registry, _ = registered
    root = repo / "evidence/visual/support"
    path = root / registry["objects"][0]["path"]
    if mutation == "tamper":
        path.write_bytes(path.read_bytes() + b" ")
    elif mutation == "missing":
        path.unlink()
    elif mutation == "unregistered":
        (root / "unexpected.json").write_text("{}")
    else:
        path.unlink()
        path.symlink_to("/etc/hosts")
    with pytest.raises((ValueError, FileNotFoundError)):
        support.validate_support(repo)


@pytest.mark.parametrize(
    "mutation", ["wrong-role", "unsafe-path", "duplicate", "extra-field", "wrong-run"]
)
def test_registry_schema_rejects_unbound_changes(registered, mutation):
    repo, registry, catalog = registered
    if mutation == "wrong-role":
        registry["objects"][0]["role"] = "private-json"
    elif mutation == "unsafe-path":
        registry["objects"][0]["path"] = "../outside.json"
    elif mutation == "duplicate":
        registry["objects"].append(copy.deepcopy(registry["objects"][0]))
    elif mutation == "extra-field":
        registry["command"] = "execute"
    else:
        registry["runs"][0]["runId"] += 1
    with pytest.raises(ValueError):
        support.validate_registry(repo, registry, catalog)


def edit_manifest(repo, entry, edit):
    path = repo / "evidence/visual" / entry["path"]
    manifest = json.loads(path.read_text())
    edit(manifest)
    raw = archive.canonical(manifest)
    path.write_bytes(raw)
    entry["sha256"] = archive.digest(raw)


@pytest.mark.parametrize("mutation", ["source", "member", "native-result", "missing-manifest"])
def test_source_member_and_native_result_bindings(registered, mutation):
    repo, registry, catalog = registered
    run = registry["runs"][0]
    if mutation == "missing-manifest":
        run["manifests"].pop()
    else:

        def edit(m):
            if mutation == "source":
                m["sourceCommit"] = "a" * 40
            elif mutation == "member":
                m["captures"][0]["archiveChain"][0]["member"] = "wrong.zip"
            else:
                c = m["captures"][0]
                c["originalOutcome"] = "passed" if c["originalOutcome"] != "passed" else "failed"
                c["outcomeEvidence"]["attemptStatuses"] = [c["originalOutcome"]]

        edit_manifest(repo, run["manifests"][0], edit)
    with pytest.raises(ValueError):
        support.validate_registry(repo, registry, catalog)


def test_standard_unknown_cannot_be_coerced_to_pass(registered):
    repo, registry, catalog = registered
    run = next(r for r in registry["runs"] if r["runId"] == 41316879851)

    def promote(m):
        c = m["captures"][0]
        c["originalOutcome"] = "passed"
        c["identityBasis"] = "native-report"
        c["outcomeEvidence"] = dict(
            basis="retained-native-report",
            project=c["project"],
            title=c["test"],
            attemptStatuses=["passed"],
        )

    edit_manifest(repo, run["manifests"][0], promote)
    with pytest.raises(ValueError, match="unknown outcome was promoted"):
        support.validate_registry(repo, registry, catalog)


def test_binding_tamper_even_with_new_hash_is_rejected(registered):
    repo, registry, catalog = registered
    descriptor = next(d for d in registry["objects"] if d["role"] == "derived-case-bindings")
    path = repo / "evidence/visual/support" / descriptor["path"]
    value = json.loads(path.read_text())
    value["bindings"][0]["attemptStatuses"] = ["passed", "failed"]
    raw = archive.canonical(value)
    digest = archive.digest(raw)
    descriptor.update(
        sha256=digest, bytes=len(raw), path=support.object_path(digest, descriptor["role"])
    )
    (repo / "evidence/visual/support" / descriptor["path"]).write_bytes(raw)
    registry["bindingsSha256"] = digest
    with pytest.raises(ValueError, match="derived native bindings mismatch"):
        support.validate_registry(repo, registry, catalog)


def test_deleting_entire_support_tree_cannot_orphan_registered_runs(registered):
    repo, _, _ = registered
    shutil.rmtree(repo / "evidence/visual/support")
    with pytest.raises(ValueError, match="missing required support registry"):
        support.validate_support(repo)


@pytest.mark.parametrize(
    "mutation", ["geometry-missing", "geometry-source", "run-outcome", "unknown-identity"]
)
def test_original_geometry_outcome_and_unknown_identity_are_bound(registered, mutation):
    repo, registry, catalog = registered
    run_id = 41316879851 if mutation == "unknown-identity" else 41314752092
    run = next(r for r in registry["runs"] if r["runId"] == run_id)

    def edit(m):
        if mutation == "geometry-missing":
            m["observations"] = []
            used = {c["sha256"] for c in m["captures"]}
            m["transfer"]["blobs"] = {h: b for h, b in m["transfer"]["blobs"].items() if h in used}
        elif mutation == "geometry-source":
            m["observations"][0]["archiveChain"][0]["member"] = "wrong.zip"
        elif mutation == "run-outcome":
            m["originalOutcome"] = "passed"
        else:
            m["captures"][0]["test"] = "invented case identity"

    edit_manifest(repo, run["manifests"][0], edit)
    with pytest.raises(ValueError):
        support.validate_registry(repo, registry, catalog)


def test_oversized_support_is_rejected_before_read(registered):
    repo, registry, catalog = registered
    descriptor = registry["objects"][0]
    path = repo / "evidence/visual/support" / descriptor["path"]
    with path.open("wb") as stream:
        stream.truncate(support.MAX_SUPPORT_BYTES + 1)
    with pytest.raises(ValueError, match="size/type bound"):
        support.load_object(repo / "evidence/visual/support", descriptor, catalog)
