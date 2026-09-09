import json
from pathlib import Path

import pytest

from digital_ocean.scripts.python.validate_deployment_evidence import (
    BASE_REQUIRED,
    TEST_REQUIRED,
    EvidenceError,
    create_manifest,
    main,
    verify_manifest,
)

COMMIT = "a" * 40


def populate(root: Path, *, tests: bool = False) -> None:
    for index, name in enumerate(BASE_REQUIRED + (TEST_REQUIRED if tests else ())):
        target = root / ("nested" if index % 2 else "") / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "post-deploy-head.txt":
            content = f"{COMMIT}\n"
        elif name == "DO_userdata.json":
            content = json.dumps(
                {
                    "droplet_id": 12345,
                    "ip_address": "192.0.2.10",
                    "user_data_sha256": "b" * 64,
                }
            )
        elif name == "deploy-mode.json":
            content = json.dumps({"effectiveMode": "full", "detectedExistingProviderId": None})
        elif name == "bootstrap-packages.txt":
            content = "ca-certificates=2026.1\ndocker.io=27.0.1\n"
        else:
            content = f"evidence:{name}\n"
        target.write_text(content, encoding="utf-8")


def test_creates_and_revalidates_complete_manifest(tmp_path):
    populate(tmp_path, tests=True)
    manifest = create_manifest(tmp_path, COMMIT, tests_required=True)
    verify_manifest(tmp_path, manifest)


@pytest.mark.parametrize("failure", ["missing", "empty", "duplicate", "symlink"])
def test_rejects_incomplete_or_ambiguous_members(tmp_path, failure):
    populate(tmp_path)
    target = next(tmp_path.rglob(BASE_REQUIRED[0]))
    if failure == "missing":
        target.unlink()
    elif failure == "empty":
        target.write_text("", encoding="utf-8")
    elif failure == "duplicate":
        duplicate = tmp_path / "duplicate" / target.name
        duplicate.parent.mkdir()
        duplicate.write_text("duplicate\n", encoding="utf-8")
    else:
        target.unlink()
        target.symlink_to(tmp_path / BASE_REQUIRED[1])
    with pytest.raises(EvidenceError):
        create_manifest(tmp_path, COMMIT, tests_required=False)


def test_detects_member_change_after_manifest_creation(tmp_path):
    populate(tmp_path)
    manifest = create_manifest(tmp_path, COMMIT, tests_required=False)
    next(tmp_path.rglob(BASE_REQUIRED[1])).write_text("changed\n", encoding="utf-8")
    with pytest.raises(EvidenceError, match="evidence_member_changed"):
        verify_manifest(tmp_path, manifest)


@pytest.mark.parametrize("tamper", ["remove", "duplicate", "traversal", "source"])
def test_rejects_tampered_manifest_structure(tmp_path, tamper):
    populate(tmp_path)
    manifest = create_manifest(tmp_path, COMMIT, tests_required=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if tamper == "remove":
        payload["files"].pop()
    elif tamper == "duplicate":
        payload["files"][-1] = payload["files"][0]
    elif tamper == "traversal":
        payload["files"][0]["path"] = "../outside"
    else:
        payload["sourceCommit"] = "b" * 40
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceError):
        verify_manifest(tmp_path, manifest)


def test_rejects_remote_source_that_does_not_match_local_candidate(tmp_path):
    populate(tmp_path)
    next(tmp_path.rglob("post-deploy-head.txt")).write_text("b" * 40 + "\n", encoding="utf-8")
    with pytest.raises(EvidenceError, match="deployed_source_mismatch"):
        create_manifest(tmp_path, COMMIT, tests_required=False)


def test_rejects_symlinked_parent_and_manifest_name_mismatch(tmp_path):
    populate(tmp_path)
    manifest = create_manifest(tmp_path, COMMIT, tests_required=False)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    nested_entry = next(entry for entry in payload["files"] if "/" in entry["path"])
    nested = tmp_path / Path(nested_entry["path"]).parent
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    nested.rename(outside)
    nested.symlink_to(outside, target_is_directory=True)
    with pytest.raises(EvidenceError, match="symlink"):
        verify_manifest(tmp_path, manifest)

    nested.unlink()
    outside.rename(nested)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["files"][0]["name"] = "wrong-name.txt"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceError, match="members|path"):
        verify_manifest(tmp_path, manifest)


def test_accepts_identical_promoted_copy_but_rejects_divergent_copy(tmp_path):
    populate(tmp_path)
    original = next(tmp_path.rglob("compose-ps.txt"))
    promoted = tmp_path / "compose-ps.txt"
    promoted.write_bytes(original.read_bytes())
    create_manifest(tmp_path, COMMIT, tests_required=False)
    promoted.write_text("different\n", encoding="utf-8")
    with pytest.raises(EvidenceError, match="required_evidence_divergent"):
        create_manifest(tmp_path, COMMIT, tests_required=False)


def test_cli_returns_bounded_failure_and_success(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--source-commit", COMMIT]) == 2
    assert capsys.readouterr().out.startswith("ERROR:")
    populate(tmp_path)
    assert main(["--root", str(tmp_path), "--source-commit", COMMIT]) == 0
    assert "remote-evidence-manifest.json" in capsys.readouterr().out


@pytest.mark.parametrize("failure", ("raw-user-data", "bad-digest", "missing-id", "id-mismatch"))
def test_provider_identity_and_user_data_digest_are_mandatory(tmp_path, failure):
    populate(tmp_path)
    userdata_path = next(tmp_path.rglob("DO_userdata.json"))
    userdata = json.loads(userdata_path.read_text(encoding="utf-8"))
    if failure == "raw-user-data":
        userdata["user_data"] = "must-not-be-retained"
    elif failure == "bad-digest":
        userdata["user_data_sha256"] = "bad"
    elif failure == "missing-id":
        userdata.pop("droplet_id")
    else:
        mode_path = next(tmp_path.rglob("deploy-mode.json"))
        mode_path.write_text(
            json.dumps({"effectiveMode": "update-only", "detectedExistingProviderId": "999"}),
            encoding="utf-8",
        )
    userdata_path.write_text(json.dumps(userdata), encoding="utf-8")
    with pytest.raises(EvidenceError, match="provider"):
        create_manifest(tmp_path, COMMIT, tests_required=False)


def test_rejects_malformed_provider_identity_json(tmp_path):
    populate(tmp_path)
    next(tmp_path.rglob("DO_userdata.json")).write_text("{", encoding="utf-8")
    with pytest.raises(EvidenceError, match="provider_evidence_invalid"):
        create_manifest(tmp_path, COMMIT, tests_required=False)
