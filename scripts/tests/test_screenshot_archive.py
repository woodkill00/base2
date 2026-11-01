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
