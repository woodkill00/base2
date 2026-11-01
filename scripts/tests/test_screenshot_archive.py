"""Archive fixtures are synthetic unit data, never native acceptance evidence."""

import copy
import io
import json
import subprocess
import zipfile

import pytest
from PIL import Image

from scripts.python import screenshot_archive as archive


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def sample(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    baseline = repo / "react-app/e2e/unit.spec.ts-snapshots/unit.png"
    baseline.parent.mkdir(parents=True)
    stream = io.BytesIO()
    Image.new("RGB", (2, 3), "black").save(stream, format="PNG")
    raw = stream.getvalue()
    baseline.write_bytes(raw)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-qm",
        "unit fixture",
    )
    commit = git(repo, "rev-parse", "HEAD")
    path = tmp_path / "native-fixture.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("case/actual.png", raw)
        z.writestr("private-not-in-inventory.txt", "excluded")
    data = dict(
        schemaVersion=1,
        repository="woodkill00/base2",
        sourceCommit=commit,
        sourceTree=git(repo, "rev-parse", "HEAD^{tree}"),
        requestedHead=commit,
        runId=11,
        attempt=1,
        jobId=22,
        artifactId=33,
        archiveSha256=archive.digest(path.read_bytes()),
        fixtureScope="synthetic-project-tests",
        originalOutcome="failed",
        technicalReview="pending",
        laterValidation="pending",
        captures=[
            dict(
                member="case/actual.png",
                sha256=archive.digest(raw),
                bytes=len(raw),
                dimensions=[2, 3],
                test="unit fixture",
                project="chromium",
                viewport=[1280, 720],
                role="actual",
                originalOutcome="failed",
                storage=f"objects/{archive.digest(raw)}.png",
            )
        ],
    )
    return repo, path, data


def test_exact_bytes_idempotent_deduplicated_and_no_baseline_change(sample):
    repo, path, data = sample
    before = git(repo, "diff", "HEAD")
    manifest = archive.import_archive(repo, path, data)
    assert archive.import_archive(repo, path, data) == manifest
    second = copy.deepcopy(data)
    second["artifactId"] += 1
    archive.import_archive(repo, path, second)
    assert archive.validate_archive(repo) == 2
    assert len(list((repo / "evidence/visual/objects").glob("*.png"))) == 1
    assert git(repo, "diff", "HEAD") == before == ""
    assert not list((repo / "evidence").rglob("*.txt"))


def test_baseline_reference_reuses_exact_historical_bytes(sample):
    repo, path, data = sample
    data["captures"][0]["storage"] = (
        f"git:{data['sourceCommit']}:react-app/e2e/unit.spec.ts-snapshots/unit.png"
    )
    archive.import_archive(repo, path, data)
    assert not (repo / "evidence/visual/objects").exists()
    assert archive.validate_archive(repo) == 1


@pytest.mark.parametrize(
    "mutation",
    ["archive", "capture", "tree", "empty", "promotion", "extra", "traversal", "size", "dimension"],
)
def test_invalid_inputs_write_nothing(sample, mutation):
    repo, path, data = sample
    if mutation == "archive":
        data["archiveSha256"] = "0" * 64
    if mutation == "capture":
        data["captures"][0]["sha256"] = "0" * 64
    if mutation == "tree":
        data["sourceTree"] = "0" * 40
    if mutation == "empty":
        data["captures"] = []
    if mutation == "promotion":
        data["technicalReview"] = "accepted"
    if mutation == "extra":
        data["signedUrl"] = "https://invalid.example"
    if mutation == "traversal":
        data["captures"][0]["member"] = "../actual.png"
    if mutation == "size":
        data["captures"][0]["bytes"] = archive.MAX_BYTES + 1
    if mutation == "dimension":
        data["captures"][0]["dimensions"] = [9, 9]
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        archive.import_archive(repo, path, data)
    assert not (repo / "evidence").exists()


def test_run_identity_cannot_replace_first_failure(sample):
    repo, path, data = sample
    target = archive.import_archive(repo, path, data)
    original = target.read_bytes()
    data["originalOutcome"] = "passed"
    with pytest.raises(ValueError, match="immutable"):
        archive.import_archive(repo, path, data)
    assert target.read_bytes() == original


def test_tampering_and_symlinks_rejected(sample, tmp_path):
    repo, path, data = sample
    archive.import_archive(repo, path, data)
    target = repo / "evidence/visual" / data["captures"][0]["storage"]
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        archive.validate_archive(repo)
    target.unlink()
    target.symlink_to(path)
    with pytest.raises(ValueError, match="symlink"):
        archive.validate_archive(repo)


def test_review_and_later_validation_are_separate_immutable_records(sample):
    repo, path, data = sample
    target = archive.import_archive(repo, path, data)
    original = target.read_bytes()
    event = dict(
        schemaVersion=1,
        kind="technical-review",
        manifest="runs/" + target.name,
        manifestSha256=archive.digest(original),
        captureHashes=[data["captures"][0]["sha256"]],
        conclusion="inconclusive",
        evidence="actual-expected-diff-pixels-inspected",
        notes="Unit fixture only; no native review claim.",
    )
    review = archive.append_event(repo, event)
    assert review.exists()
    event.update(kind="native-validation", conclusion="passed", evidence="runs/" + target.name)
    with pytest.raises(ValueError):
        archive.append_event(repo, event)
    later = copy.deepcopy(data)
    later.update(runId=12, originalOutcome="passed")
    later["captures"][0]["originalOutcome"] = "passed"
    result = archive.import_archive(repo, path, later)
    event["evidence"] = "runs/" + result.name
    archive.append_event(repo, event)
    assert archive.validate_archive(repo) == 2
    assert target.read_bytes() == original
    assert json.loads(original)["originalOutcome"] == "failed"
    assert json.loads(original)["technicalReview"] == "pending"


def test_duplicate_zip_members_rejected(sample):
    repo, path, data = sample
    with zipfile.ZipFile(path, "a") as z, pytest.warns(UserWarning):
        z.writestr("case/actual.png", b"bad")
    data["archiveSha256"] = archive.digest(path.read_bytes())
    with pytest.raises(ValueError, match="duplicate ZIP"):
        archive.import_archive(repo, path, data)


def test_non_png_bytes_cannot_be_archived(sample):
    repo, path, data = sample
    raw = b"not an image"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("case/actual.png", raw)
    data["archiveSha256"] = archive.digest(path.read_bytes())
    c = data["captures"][0]
    c.update(
        sha256=archive.digest(raw), bytes=len(raw), storage=f"objects/{archive.digest(raw)}.png"
    )
    with pytest.raises(ValueError, match="invalid PNG"):
        archive.import_archive(repo, path, data)


def test_inventory_covers_explicit_and_automatic_screenshot_producers():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    inventory = json.loads(
        (root / "specs/124-shared-workspace-policy/screenshot-inventory.json").read_text()
    )
    actual = set()
    for directory in ("react-app/e2e", "e2e"):
        for path in (root / directory).rglob("*"):
            if (
                path.is_file()
                and path.suffix in {".ts", ".js", ".mjs"}
                and "node_modules" not in path.parts
                and re.search(r"toHaveScreenshot|\.screenshot\(", path.read_text())
            ):
                actual.add(path.relative_to(root).as_posix())
    assert {item["path"] for item in inventory["explicitCaptureSources"]} == actual
    automatic = {
        path.relative_to(root).as_posix()
        for path in (root / "react-app").glob("*config*")
        if path.is_file() and re.search(r"screenshot:\s*'only-on-failure'", path.read_text())
    }
    assert {item["path"] for item in inventory["automaticFailureConfigurations"]} == automatic
    assert (
        "scripts/tests/test_screenshot_archive.py"
        in (root / ".github/workflows/ci-backend.yml").read_text()
    )


def test_crc_valid_but_undecodable_png_is_rejected(sample):
    import struct
    import zlib

    repo, path, data = sample
    raw = (repo / "react-app/e2e/unit.spec.ts-snapshots/unit.png").read_bytes()
    chunks = [raw[:8]]
    offset = 8
    while offset < len(raw):
        size = struct.unpack(">I", raw[offset : offset + 4])[0]
        kind = raw[offset + 4 : offset + 8]
        payload = raw[offset + 8 : offset + 8 + size]
        if kind == b"IDAT":
            payload = b"not a valid zlib stream"
        chunks.append(
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )
        offset += size + 12
    broken = b"".join(chunks)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("case/actual.png", broken)
    data["archiveSha256"] = archive.digest(path.read_bytes())
    data["captures"][0].update(
        sha256=archive.digest(broken),
        bytes=len(broken),
        storage=f"objects/{archive.digest(broken)}.png",
    )
    with pytest.raises(OSError):
        archive.import_archive(repo, path, data)
    assert not (repo / "evidence").exists()


def transfer_manifest(repo, data):
    """Only a synthetic unit Git object, never native evidence."""
    raw = (repo / "react-app/e2e/unit.spec.ts-snapshots/unit.png").read_bytes()
    blob = (
        subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input=raw, cwd=repo)
        .decode()
        .strip()
    )
    path = repo / "evidence/visual/objects" / (data["captures"][0]["sha256"] + ".png")
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    git(repo, "add", str(path.relative_to(repo)))
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-qm",
        "unit transfer",
    )
    path.unlink()
    data["transfer"] = dict(
        commit=git(repo, "rev-parse", "HEAD"),
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        originalArchiveVerification="externally-verified-zip-and-members",
        localVerification="git-blob-sha256-size-dimensions-full-decode",
        blobs={data["captures"][0]["sha256"]: blob},
    )
    return data


def test_git_transfer_retains_external_zip_verification_and_exact_bytes(sample):
    repo, path, data = sample
    transfer_manifest(repo, data)
    path.unlink()  # Original ZIP deliberately unavailable in this verifier.
    target = archive.import_git_transfer(repo, data)
    assert (
        json.loads(target.read_bytes())["transfer"]["originalArchiveVerification"]
        == "externally-verified-zip-and-members"
    )
    assert archive.validate_archive(repo) == 1
    assert archive.import_git_transfer(repo, data) == target


@pytest.mark.parametrize("fault", ["tree", "blob", "size", "dimensions", "claim"])
def test_git_transfer_rejects_invalid_provenance_before_manifest_write(sample, fault):
    repo, _, data = sample
    transfer_manifest(repo, data)
    if fault == "tree":
        data["transfer"]["tree"] = "0" * 40
    elif fault == "blob":
        data["transfer"]["blobs"][data["captures"][0]["sha256"]] = "0" * 40
    elif fault == "size":
        data["captures"][0]["bytes"] += 1
    elif fault == "dimensions":
        data["captures"][0]["dimensions"] = [5, 5]
    else:
        data["transfer"]["originalArchiveVerification"] = "locally-verified"
    with pytest.raises(ValueError):
        archive.import_git_transfer(repo, data)
    assert not (repo / "evidence/visual/runs").exists()


def test_zip_and_transfer_verification_cannot_be_conflated(sample):
    repo, path, data = sample
    with pytest.raises(ValueError, match="explicit Git transfer"):
        archive.import_git_transfer(repo, data)
    transfer_manifest(repo, data)
    with pytest.raises(ValueError, match="ZIP import cannot claim"):
        archive.import_archive(repo, path, data)


def test_source_proof_survives_absent_merge_object_and_rejects_tampering(sample, monkeypatch):
    import hashlib

    repo, path, data = sample
    # A synthetic merge object is retained as bytes, never written to Git object storage.
    raw = (
        f"tree {data['sourceTree']}\nparent {data['requestedHead']}\n"
        "author Fixture <fixture@example.invalid> 1 +0000\n"
        "committer Fixture <fixture@example.invalid> 1 +0000\n\nunit source proof\n"
    ).encode()
    commit = hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    data["sourceCommit"] = commit
    proof = repo / "evidence/visual/sources" / (commit + ".commit")
    proof.parent.mkdir(parents=True)
    proof.write_bytes(raw)
    archive.import_archive(repo, path, data)
    assert archive.validate_archive(repo) == 1
    proof.write_bytes(raw + b"tampered")
    with pytest.raises(ValueError, match="source proof identity"):
        archive.validate_archive(repo)


def test_retained_data_ci_has_history_no_persistent_credentials_or_network_fetch():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci-backend.yml").read_text())
    steps = workflow["jobs"]["backend"]["steps"]
    checkout = next(step for step in steps if step.get("name") == "Checkout")
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    verify = next(
        step
        for step in steps
        if step.get("name") == "Validate retained screenshot archive integrity"
    )
    assert verify["if"] == "matrix.service == 'api'"
    assert verify["run"] == "python -m scripts.python.screenshot_archive --repo . --require-runs"
    assert "continue-on-error" not in verify
    assert steps.index(verify) > next(
        i for i, step in enumerate(steps) if step.get("name") == "Install deps"
    )


def test_ci_mode_rejects_missing_run_manifests(tmp_path):
    import sys
    from pathlib import Path

    tool = Path(__file__).resolve().parents[2] / "scripts/python/screenshot_archive.py"
    result = subprocess.run(
        [sys.executable, str(tool), "--repo", str(tmp_path), "--require-runs"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "required archive has no run manifests" in result.stderr


def v2_manifest(repo, data):
    transfer_manifest(repo, data)
    data.update(schemaVersion=2, observations=[])
    for c in data["captures"]:
        c["member"] = "case/unit-actual.png"
        c.update(
            archiveChain=[
                {
                    "member": "project.zip",
                    "sha256": "a" * 64,
                    "hashBasis": "externally-verified-original-member",
                },
                {
                    "member": c["member"],
                    "sha256": c["sha256"],
                    "hashBasis": "externally-verified-original-member",
                },
            ],
            identityBasis="native-report",
            viewportBasis="native-project-config",
            outcomeEvidence={
                "basis": "retained-native-report",
                "project": c["project"],
                "title": c["test"],
                "attemptStatuses": [c["originalOutcome"]],
            },
        )
    return data


def test_v2_roundtrip_nested_chain_and_unknown_remain_diagnostic(sample):
    repo, _, data = sample
    v2_manifest(repo, data)
    c = data["captures"][0]
    c.update(
        originalOutcome="unknown",
        identityBasis="archive-directory",
        viewport=None,
        viewportBasis="unavailable",
        outcomeEvidence={"basis": "per-case-result-unavailable"},
    )
    target = archive.import_git_transfer(repo, data)
    assert json.loads(target.read_bytes()) == data
    assert archive.validate_archive(repo) == 1
    assert data["laterValidation"] == data["technicalReview"] == "pending"
    # Committed integrity does not need an unreferenced transfer object to survive.
    data["transfer"]["commit"] = "f" * 40
    target.write_bytes(archive.canonical(data))
    assert archive.validate_archive(repo) == 1


@pytest.mark.parametrize(
    "fault", ["traversal", "leaf", "unknown", "mixed-role", "viewport", "missing-inner-hash"]
)
def test_v2_invalid_provenance_writes_no_manifest(sample, fault):
    repo, _, data = sample
    v2_manifest(repo, data)
    c = data["captures"][0]
    if fault == "traversal":
        c["archiveChain"][0]["member"] = "../escape.zip"
    if fault == "leaf":
        c["archiveChain"][-1]["sha256"] = "b" * 64
    if fault == "unknown":
        c["originalOutcome"] = "unknown"
    if fault == "mixed-role":
        c["role"] = "expected"
    if fault == "viewport":
        c["viewportBasis"] = "unavailable"
    if fault == "missing-inner-hash":
        c["archiveChain"][0]["sha256"] = None
    with pytest.raises(ValueError):
        archive.import_git_transfer(repo, data)
    assert not (repo / "evidence/visual/runs").exists()


def test_v2_observation_import_exact_original_schema_tamper_and_private_rejected(sample, tmp_path):
    from scripts.tests.test_visual_matrix_artifacts import media_observation_fixture

    repo, _, data = sample
    v2_manifest(repo, data)
    _, _, _, observation, _ = media_observation_fixture(tmp_path)
    raw = observation.read_bytes()
    sha = archive.digest(raw)
    path = repo / f"evidence/visual/observations/{sha}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    git(repo, "add", str(path.relative_to(repo)))
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-qm",
        "unit geometry",
    )
    data["transfer"].update(
        commit=git(repo, "rev-parse", "HEAD"), tree=git(repo, "rev-parse", "HEAD^{tree}")
    )
    data["transfer"]["blobs"][sha] = git(repo, "rev-parse", f"HEAD:{path.relative_to(repo)}")
    c = data["captures"][0]
    c["project"] = c["outcomeEvidence"]["project"] = "chromium-desktop"
    item = dict(
        member="case/media-viewport-observations.json",
        sha256=sha,
        bytes=len(raw),
        storage=f"observations/{sha}.json",
        project="chromium-desktop",
        schemaVersion=1,
        archiveChain=[
            dict(
                member="case/media-viewport-observations.json",
                sha256=sha,
                hashBasis="externally-verified-original-member",
            )
        ],
    )
    data["observations"] = [item]
    path.unlink()
    archive.import_git_transfer(repo, data)
    assert path.read_bytes() == raw
    assert archive.validate_archive(repo) == 1
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="observation integrity"):
        archive.validate_archive(repo)
    private = json.loads(raw)
    private["privateUrl"] = "secret"
    altered = archive.canonical(private)
    with pytest.raises(ValueError, match="observation schema"):
        archive.validate_observation_bytes(
            altered, {**item, "sha256": archive.digest(altered), "bytes": len(altered)}
        )


def test_v2_scoped_review_binds_members_roles_and_rejects_uninspected(sample):
    repo, _, data = sample
    v2_manifest(repo, data)
    expected = copy.deepcopy(data["captures"][0])
    expected.update(member="case/unit-expected.png", role="expected")
    expected["archiveChain"][-1]["member"] = expected["member"]
    data["captures"].append(expected)  # Deliberately identical unit bytes, distinct roles.
    path = archive.import_git_transfer(repo, data)
    c = data["captures"][0]
    event = dict(
        schemaVersion=2,
        kind="technical-review",
        manifest="runs/" + path.name,
        manifestSha256=archive.digest(path.read_bytes()),
        conclusion="inconclusive",
        notes="Synthetic unit inspection subset; never native acceptance.",
        inspections=[
            dict(member=c["member"], sha256=c["sha256"], role="actual", method="individual-pixels")
        ],
    )
    archive.append_event(repo, event)
    assert archive.validate_archive(repo) == 1
    bad = copy.deepcopy(event)
    bad["inspections"][0]["role"] = "expected"
    with pytest.raises(ValueError, match="mixed-role"):
        archive.validate_event(repo, bad)
    bad = copy.deepcopy(event)
    bad["inspections"][0]["method"] = "uninspected"
    with pytest.raises(ValueError, match="uninspected"):
        archive.validate_event(repo, bad)
    legacy = dict(
        schemaVersion=1,
        kind="technical-review",
        manifest=event["manifest"],
        manifestSha256=event["manifestSha256"],
        captureHashes=[c["sha256"]],
        conclusion="inconclusive",
        notes=event["notes"],
        evidence="actual-expected-diff-pixels-inspected",
    )
    with pytest.raises(ValueError, match="member-role"):
        archive.validate_event(repo, legacy)


def test_unknown_case_cannot_be_promoted_by_later_native_event(sample):
    repo, _, data = sample
    v2_manifest(repo, data)
    c = data["captures"][0]
    c.update(
        originalOutcome="unknown",
        identityBasis="archive-directory",
        outcomeEvidence={"basis": "per-case-result-unavailable"},
    )
    target = archive.import_git_transfer(repo, data)
    later = copy.deepcopy(data)
    later["runId"] += 1
    later["originalOutcome"] = "passed"
    native = later["captures"][0]
    native.update(
        originalOutcome="passed",
        identityBasis="native-report",
        outcomeEvidence={
            "basis": "retained-native-report",
            "project": native["project"],
            "title": native["test"],
            "attemptStatuses": ["passed"],
        },
    )
    validation = archive.import_git_transfer(repo, later)
    event = dict(
        schemaVersion=1,
        kind="native-validation",
        manifest="runs/" + target.name,
        manifestSha256=archive.digest(target.read_bytes()),
        captureHashes=[c["sha256"]],
        conclusion="passed",
        evidence="runs/" + validation.name,
        notes="Synthetic rejection fixture.",
    )
    with pytest.raises(ValueError, match="unknown evidence"):
        archive.append_event(repo, event)
    assert not (repo / "evidence/visual/events").exists()


def test_batch_review_rejects_all_before_writing_any(sample):
    repo, _, data = sample
    v2_manifest(repo, data)
    target = archive.import_git_transfer(repo, data)
    c = data["captures"][0]
    event = dict(
        schemaVersion=2,
        kind="technical-review",
        manifest="runs/" + target.name,
        manifestSha256=archive.digest(target.read_bytes()),
        conclusion="inconclusive",
        notes="Synthetic batch; no native acceptance.",
        inspections=[
            dict(member=c["member"], sha256=c["sha256"], role=c["role"], method="individual-pixels")
        ],
    )
    invalid = copy.deepcopy(event)
    invalid["inspections"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        archive.append_events(repo, [event, invalid])
    assert not (repo / "evidence/visual/events").exists()
