"""Local originals close diagnostic dependencies without fabricated Git transfer."""

import copy
import io
import json
import zipfile

import pytest

from scripts.python import local_capture_proof as local
from scripts.python import screenshot_archive as a
from scripts.python import typed_archive_support as typed
from scripts.tests.test_screenshot_archive import sample  # noqa: F401
from scripts.tests.test_typed_archive_support import bundle  # noqa: F401


@pytest.fixture
def local_bundle(bundle, tmp_path):  # noqa: F811
    repo, root, old = bundle
    registry = copy.deepcopy(old)
    registry.update(schemaVersion=6, kind="local-zip-diagnostic-validation")
    row = registry["bundles"][0]
    old_manifest = json.loads((repo / "evidence/visual" / row["manifests"][0]["path"]).read_bytes())
    capture = old_manifest["captures"][0]
    png = a.storage_bytes(repo, capture["storage"])
    receipt = row["receipts"][0]
    raw = (root / receipt["path"]).read_bytes()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr(capture["member"], png)
        z.writestr(receipt["member"], raw)
        z.comment = b"UNAPPROVED-CONTAINER-PAYLOAD"
    archive = stream.getvalue()
    archive_sha = a.digest(archive)
    receipt["archiveSha256"] = archive_sha
    local_root = tmp_path / "local-originals"
    (local_root / "transport").mkdir(parents=True)
    (local_root / "transport" / f"{archive_sha}.zip").write_bytes(archive)
    job = dict(
        runId=str(row["runId"]),
        attempt=row["attempt"],
        jobId=old_manifest["jobId"],
        requestedHead=row["requestedHead"],
        originalReadSHA256="e" * 64,
    )
    jobs_raw = json.dumps(dict(runs=[job])).encode()
    identity = {
        k: row[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    artifact = dict(
        identity, artifactId=33, archiveSha256=archive_sha, bytes=len(archive), jobId=job["jobId"]
    )
    artifacts_raw = json.dumps(dict(artifacts=[artifact])).encode()
    context = local.LocalZipContext(
        local_root, jobs_raw, a.digest(jobs_raw), artifacts_raw, a.digest(artifacts_raw)
    )
    frame = dict(
        member=capture["member"],
        sha256=a.digest(png),
        bytes=len(png),
        dimensions=a.png(png),
        project=row["project"],
        test=capture["test"],
        originalOutcome="unknown",
        storage=f"local-zip:{archive_sha}:{a.digest(png)}.png",
        archiveChain=[
            dict(
                member=capture["member"],
                sha256=a.digest(png),
                hashBasis="externally-verified-original-member",
            )
        ],
    )
    manifest = dict(
        identity,
        schemaVersion=3,
        kind=local.PROFILE,
        repository="woodkill00/base2",
        jobId=job["jobId"],
        artifactId=33,
        archiveSha256=archive_sha,
        jobIndexSha256=a.digest(jobs_raw),
        jobReadSha256="e" * 64,
        suite=row["suite"],
        case=row["case"],
        project=row["project"],
        fixtureScope="synthetic-project-tests",
        originalOutcome="unknown",
        captures=[frame],
        acceptance=False,
        runComplete=False,
    )
    path = f"local-manifests/{a.digest(json.dumps(manifest).encode())}.json"
    (root / "local-manifests").mkdir()
    (root / path).write_bytes(json.dumps(manifest).encode())
    row["manifests"] = [dict(path=path, sha256=a.digest((root / path).read_bytes()))]
    return repo, root, registry, context, manifest


def update_manifest(root, registry, manifest):
    entry = registry["bundles"][0]["manifests"][0]
    raw = json.dumps(manifest).encode()
    entry["sha256"] = a.digest(raw)
    entry["path"] = f"local-manifests/{entry['sha256']}.json"
    (root / entry["path"]).write_bytes(raw)


def test_local_registry_keeps_failure_unknown_and_no_persistent_writes(local_bundle):
    repo, root, registry, context, manifest = local_bundle
    before = {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    for _ in range(2):
        result = typed.validate_local_registry(repo, registry, root, context)
        assert result["dependencyComplete"] is True
        assert result["acceptance"] is False and result["runComplete"] is False
    assert before == {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    receipt = json.loads((root / registry["bundles"][0]["receipts"][0]["path"]).read_bytes())
    assert receipt["incomplete"] and receipt["errors"] == ["body-failed", "coverage-incomplete"]
    assert manifest["captures"][0]["originalOutcome"] == "unknown"
    with pytest.raises(ValueError):
        typed.validate_registry(repo, registry, root)
    with pytest.raises(ValueError):
        typed.register(repo, json.dumps(registry).encode(), root)
    with pytest.raises(ValueError):
        a.validate_manifest(manifest)


@pytest.mark.parametrize(
    "fault",
    ["job", "artifact", "source", "project", "member", "hash", "dimensions", "transfer", "outcome"],
)
def test_local_crossbinding_rejects(local_bundle, fault):
    repo, root, registry, context, manifest = local_bundle
    if fault == "job":
        manifest["jobId"] += 1
    elif fault == "artifact":
        context.artifacts[0]["artifactId"] += 1
    elif fault == "source":
        context.artifacts[0]["sourceTree"] = "f" * 40
    elif fault == "project":
        manifest["captures"][0]["project"] = "webkit-mobile"
    elif fault == "member":
        manifest["captures"][0]["archiveChain"][-1]["member"] = "another/actual.png"
    elif fault == "hash":
        manifest["captures"][0]["archiveChain"][-1]["sha256"] = "f" * 64
    elif fault == "dimensions":
        manifest["captures"][0]["dimensions"] = [123, 456]
    elif fault == "transfer":
        manifest["transfer"] = {"commit": "a" * 40}
    elif fault == "outcome":
        manifest["captures"][0]["originalOutcome"] = "passed"
    update_manifest(root, registry, manifest)
    with pytest.raises(ValueError):
        typed.validate_local_registry(repo, registry, root, context)


@pytest.mark.parametrize("missing", ["archive", "receipt", "manifest"])
def test_missing_local_dependencies_remain_incomplete(local_bundle, missing):
    repo, root, registry, context, manifest = local_bundle
    if missing == "archive":
        (context.root / "transport" / f"{manifest['archiveSha256']}.zip").unlink()
    elif missing == "receipt":
        (root / registry["bundles"][0]["receipts"][0]["path"]).unlink()
    else:
        (root / registry["bundles"][0]["manifests"][0]["path"]).unlink()
    result = typed.validate_local_registry(repo, registry, root, context)
    assert (
        not result["dependencyComplete"] and not result["acceptance"] and not result["runComplete"]
    )
    assert result["errors"] and not result["paths"]


def test_local_trusted_indexes_cannot_be_self_substituted(local_bundle):
    _, _, _, context, _ = local_bundle
    with pytest.raises(ValueError, match="job index identity"):
        local.LocalZipContext(context.root, b'{"runs":[]}', "e" * 64, b"{}", "f" * 64)


def test_git_schema2_still_requires_real_transfer(local_bundle):
    _, _, _, _, manifest = local_bundle
    with pytest.raises(ValueError):
        a.validate_capture_manifest(manifest, profile="git")
    with pytest.raises(ValueError):
        a.validate_capture_manifest(manifest, profile="automatic")


def rebind_archive(root, registry, context, manifest, body, prefix=None):
    sha = a.digest(body)
    manifest["archiveSha256"] = sha
    for frame in manifest["captures"]:
        frame["storage"] = f"local-zip:{sha}:{frame['sha256']}.png"
        if prefix:
            frame["archiveChain"].insert(0, prefix.copy())
    for entry in registry["bundles"][0]["receipts"]:
        entry["archiveSha256"] = sha
        if prefix:
            entry["archiveChain"].insert(0, prefix.copy())
    context.artifacts[0].update(archiveSha256=sha, bytes=len(body))
    (context.root / "transport" / f"{sha}.zip").write_bytes(body)
    update_manifest(root, registry, manifest)


def test_nested_local_original_chain_and_hashes(local_bundle):
    repo, root, registry, context, manifest = local_bundle
    inner = (context.root / "transport" / f"{manifest['archiveSha256']}.zip").read_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr("chromium-compact.zip", inner)
        z.writestr("unapproved-private.json", b'{"private":"NEVER-RETAIN"}')
    prefix = dict(
        member="chromium-compact.zip",
        sha256=a.digest(inner),
        hashBasis="externally-verified-original-member",
    )
    rebind_archive(root, registry, context, manifest, output.getvalue(), prefix)
    before = {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert typed.validate_local_registry(repo, registry, root, context)["dependencyComplete"]
    assert before == {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    manifest["captures"][0]["archiveChain"][0]["sha256"] = "f" * 64
    update_manifest(root, registry, manifest)
    with pytest.raises(ValueError, match="member digest"):
        typed.validate_local_registry(repo, registry, root, context)


def test_private_receipt_body_rejected_without_repository_writes(local_bundle):
    repo, root, registry, context, manifest = local_bundle
    entry = registry["bundles"][0]["receipts"][0]
    data = json.loads((root / entry["path"]).read_bytes())
    data["private"] = "NOT-A-NATIVE-FIELD"
    raw = json.dumps(data).encode()
    sha = a.digest(raw)
    entry.update(path=f"objects/{sha}.json", sha256=sha, bytes=len(raw))
    entry["archiveChain"][-1]["sha256"] = sha
    (root / entry["path"]).write_bytes(raw)
    original = (context.root / "transport" / f"{manifest['archiveSha256']}.zip").read_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as z, zipfile.ZipFile(output, "w") as out:
        for info in z.infolist():
            out.writestr(info.filename, raw if info.filename == entry["member"] else z.read(info))
    rebind_archive(root, registry, context, manifest, output.getvalue())
    before = {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    with pytest.raises(ValueError):
        typed.validate_local_registry(repo, registry, root, context)
    assert before == {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate-job",
        "duplicate-artifact",
        "artifact-job",
        "artifact-size",
        "artifact-run",
        "metadata-bytes",
        "duplicate-zip",
    ],
)
def test_local_original_indexes_and_metadata_cannot_drift(local_bundle, fault):
    repo, root, registry, context, manifest = local_bundle
    if fault == "duplicate-job":
        context.jobs.append(copy.deepcopy(context.jobs[0]))
    elif fault == "duplicate-artifact":
        context.artifacts.append(copy.deepcopy(context.artifacts[0]))
    elif fault == "artifact-job":
        context.artifacts[0]["jobId"] += 1
    elif fault == "artifact-size":
        context.artifacts[0]["bytes"] += 1
    elif fault == "artifact-run":
        context.artifacts[0]["runId"] += 1
    elif fault == "metadata-bytes":
        (root / registry["bundles"][0]["receipts"][0]["path"]).write_bytes(b"{}")
    else:
        original = (context.root / "transport" / f"{manifest['archiveSha256']}.zip").read_bytes()
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original)) as z, zipfile.ZipFile(output, "w") as out:
            for info in z.infolist():
                out.writestr(info.filename, z.read(info))
            with pytest.warns(UserWarning):
                out.writestr(manifest["captures"][0]["member"], b"duplicate")
        rebind_archive(root, registry, context, manifest, output.getvalue())
    with pytest.raises(ValueError):
        typed.validate_local_registry(repo, registry, root, context)


def test_backend_neutral_capture_plan_translates_without_fabricated_transfer(local_bundle):
    repo, root, registry, context, manifest = local_bundle
    frame = manifest["captures"][0]
    plan = {
        k: manifest[k]
        for k in (
            "sourceCommit",
            "sourceTree",
            "requestedHead",
            "runId",
            "attempt",
            "jobId",
            "suite",
            "case",
        )
    }
    plan.update(
        projectCandidates=[manifest["project"]],
        captureDescriptors=[
            dict(
                artifactId=manifest["artifactId"],
                runId=str(manifest["runId"]),
                artifactZipSha256=manifest["archiveSha256"],
                archiveMemberChain=[dict(member=frame["member"])],
                sha256=frame["sha256"],
                sizeBytes=frame["bytes"],
                pixels=dict(zip(("width", "height"), frame["dimensions"], strict=True)),
                project=frame["project"],
                test=frame["test"],
                nativeOutcome=None,
                nativeTestBindingStatus="unknown-not-inferred-from-filename",
            )
        ],
    )
    planned = local.plan_capture_manifests(plan, context)
    assert planned == [manifest] and "transfer" not in planned[0]
    assert a.capture_storage_bytes(
        repo, manifest, frame, profile="local-zip", local_context=context
    )
    plan["captureDescriptors"][0]["nativeOutcome"] = "passed"
    with pytest.raises(ValueError):
        local.plan_capture_manifests(plan, context)


def test_local_registry_cannot_silently_substitute_git_profile(local_bundle):
    repo, root, registry, _, _ = local_bundle
    with pytest.raises(ValueError, match="explicit local ZIP context"):
        typed.validate_local_registry(repo, registry, root, None)


def test_local_metadata_only_owner_retains_declared_not_required(local_bundle):
    repo, root, registry, context, manifest = local_bundle
    entry = registry["bundles"][0]["receipts"][0]
    data = json.loads((root / entry["path"]).read_bytes())
    data.update(frames=[], errors=[], incomplete=False, revoked=False, hookStarted=False)
    data["coverage"] = {key: "not-required" for key in data["coverage"]}
    raw = json.dumps(data).encode()
    sha = a.digest(raw)
    entry.update(path=f"objects/{sha}.json", sha256=sha, bytes=len(raw))
    entry["archiveChain"][-1]["sha256"] = sha
    (root / entry["path"]).write_bytes(raw)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr(entry["member"], raw)
    rebind_archive(root, registry, context, manifest, output.getvalue())
    registry["bundles"][0]["manifests"] = []
    result = typed.validate_local_registry(repo, registry, root, context)
    assert result["dependencyComplete"] and not result["runComplete"] and not result["acceptance"]
    assert local.plan_capture_manifests({"captureDescriptors": []}, context) == []


def binding_plan(fixture):
    _, root, registry, context, manifest = fixture
    row = registry["bundles"][0]
    data = dict(
        schemaVersion=1,
        fixtureScope="synthetic-project-tests",
        scope="Diagnostic continuous viewports; not visual acceptance.",
        sourceCommit=manifest["sourceCommit"],
        sourceTree=manifest["sourceTree"],
        runId=str(manifest["runId"]),
        attempt=str(manifest["attempt"]),
        project=manifest["project"],
        test=manifest["captures"][0]["test"],
        route="/workspace",
        state="current",
        target="content-scrollport",
        extent=1000,
        segmentLimit=64,
        reachedEnd=False,
        complete=False,
        errors=["empty"],
        segments=[],
    )
    raw = json.dumps(data).encode()
    receipt = row["receipts"][0]
    receipt.update(
        path=f"objects/{a.digest(raw)}.json",
        sha256=a.digest(raw),
        bytes=len(raw),
        family="continuous",
        schemaVersion=1,
        member=manifest["case"] + "/continuous-current.json",
    )
    receipt["archiveChain"] = [
        dict(
            member=receipt["member"],
            sha256=receipt["sha256"],
            hashBasis="externally-verified-original-member",
        )
    ]
    image = a.capture_storage_bytes(
        fixture[0], manifest, manifest["captures"][0], profile="local-zip", local_context=context
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr(manifest["captures"][0]["member"], image)
        z.writestr(receipt["member"], raw)
    rebind_archive(root, registry, context, manifest, output.getvalue())
    (root / receipt["path"]).write_bytes(raw)
    plan = {
        k: manifest[k]
        for k in (
            "sourceCommit",
            "sourceTree",
            "requestedHead",
            "runId",
            "attempt",
            "jobId",
            "suite",
            "case",
        )
    }
    plan["projectCandidates"] = [manifest["project"]]

    def location(entry, size):
        return dict(
            artifactId=33,
            runId=str(manifest["runId"]),
            artifactZipSha256=manifest["archiveSha256"],
            archiveMemberChain=[dict(member=entry["member"])],
            sha256=entry["sha256"],
            sizeBytes=size,
        )

    frame = manifest["captures"][0]
    capture = location(frame, frame["bytes"])
    capture.update(
        pixels=dict(zip(("width", "height"), frame["dimensions"], strict=True)),
        project=frame["project"],
        test=frame["test"],
        nativeOutcome=None,
        nativeTestBindingStatus="exact-project-title",
    )
    plan["captureDescriptors"] = [capture]
    receipt = row["receipts"][0]
    plan["receiptDescriptors"] = [
        dict(
            sha256=receipt["sha256"],
            bytes=receipt["bytes"],
            family=receipt["family"],
            schemaVersion=receipt["schemaVersion"],
            originalLocations=[location(receipt, receipt["bytes"])],
        )
    ]
    return plan


def test_exact_title_binding_uses_validated_original_and_keeps_plan(local_bundle):
    repo, _, _, context, _ = local_bundle
    plan = binding_plan(local_bundle)
    original = copy.deepcopy(plan)
    with pytest.raises(ValueError, match="outcome binding"):
        local.plan_capture_manifests(plan, context)
    binding = local.derive_plan_binding(repo, plan, context)
    result = local.plan_capture_manifests(plan, context, binding=binding)
    assert plan == original
    assert result[0]["captures"][0]["originalOutcome"] == "unknown"
    assert result[0]["runComplete"] is False


@pytest.mark.parametrize(
    "fault", ["title", "project", "outcome", "empty", "conflicting", "receipt-hash", "source"]
)
def test_explicit_binding_rejects_wrong_original_or_plan(local_bundle, fault):
    repo, _, _, context, _ = local_bundle
    plan = binding_plan(local_bundle)
    if fault == "title":
        plan["captureDescriptors"][0]["test"] = "wrong"
    elif fault == "project":
        plan["captureDescriptors"][0]["project"] = "webkit-mobile"
    elif fault == "outcome":
        plan["captureDescriptors"][0]["nativeOutcome"] = "passed"
    elif fault == "empty":
        plan["receiptDescriptors"] = []
    elif fault == "conflicting":
        plan["projectCandidates"] = ["webkit-mobile"]
    elif fault == "receipt-hash":
        plan["receiptDescriptors"][0]["sha256"] = "f" * 64
    else:
        plan["sourceTree"] = "f" * 40
    with pytest.raises(ValueError):
        binding = local.derive_plan_binding(repo, plan, context)
        local.plan_capture_manifests(plan, context, binding=binding)


def test_explicit_receipt_derives_separate_project_without_mutating_empty_plan(local_bundle):
    repo, _, _, context, _ = local_bundle
    plan = binding_plan(local_bundle)
    plan["projectCandidates"] = []
    binding = local.derive_plan_binding(repo, plan, context)
    assert (
        local.plan_capture_manifests(plan, context, binding=binding)[0]["project"]
        == binding.project
    )
    assert plan["projectCandidates"] == []
    plan["captureDescriptors"][0]["test"] = "changed after validation"
    with pytest.raises(ValueError, match="unchanged plan"):
        local.plan_capture_manifests(plan, context, binding=binding)


@pytest.mark.parametrize(
    "bad_case",
    [
        "/tmp/escaped-plan-case",
        "../escaped-plan-case",
        "case/../escape",
        "./case",
        "case/",
        "case//nested",
        "",
        ".",
        "..",
        "case\\escape",
        "case\n",
        "unknown-producer",
    ],
)
def test_invalid_plan_case_has_no_filesystem_operations(local_bundle, monkeypatch, bad_case):
    import tempfile

    repo, _, _, context, _ = local_bundle
    plan = dict(
        suite="workspace",
        case=bad_case,
        projectCandidates=[],
        captureDescriptors=[],
        receiptDescriptors=[],
    )

    def forbidden(*args, **kwargs):
        pytest.fail("filesystem work before producer validation")

    monkeypatch.setattr(tempfile, "TemporaryDirectory", forbidden)
    monkeypatch.setattr(a, "verify_source", forbidden)
    with pytest.raises(ValueError, match="planned .*producer"):
        local.derive_plan_binding(repo, plan, context)


@pytest.mark.parametrize(
    "field,value",
    [
        ("suite", "unknown"),
        ("projectCandidates", ["bogus"]),
        ("projectCandidates", ["chromium-compact", "webkit-mobile"]),
        ("projectCandidates", [None]),
    ],
)
def test_invalid_plan_registration_precedes_filesystem(local_bundle, monkeypatch, field, value):
    import tempfile

    repo, _, _, context, manifest = local_bundle
    plan = dict(
        suite=manifest["suite"],
        case=manifest["case"],
        projectCandidates=[manifest["project"]],
        captureDescriptors=[],
        receiptDescriptors=[],
    )
    plan[field] = value

    def forbidden(*args, **kwargs):
        pytest.fail("filesystem work before registration")

    monkeypatch.setattr(tempfile, "TemporaryDirectory", forbidden)
    monkeypatch.setattr(a, "verify_source", forbidden)
    with pytest.raises(ValueError):
        local.derive_plan_binding(repo, plan, context)


@pytest.mark.parametrize(
    "order", ["sequence-first", "continuous-first", "external-dependency", "missing", "foreign"]
)
def test_two_phase_dependency_materialization(local_bundle, monkeypatch, order):
    """Adapter orchestration; real family validators have separate existing tests."""
    repo, root, registry, context, manifest = local_bundle
    plan = binding_plan(local_bundle)
    continuous = plan["receiptDescriptors"][0]
    seq = dict(continuous)
    seqraw = json.dumps(
        dict(
            binding=dict(
                project=manifest["project"], test=manifest["captures"][0]["test"], state="current"
            )
        )
    ).encode()
    seq.update(family="sequence", sha256=a.digest(seqraw), bytes=len(seqraw))
    loc = dict(continuous["originalLocations"][0])
    loc.update(
        sha256=seq["sha256"],
        sizeBytes=len(seqraw),
        archiveMemberChain=[dict(member=manifest["case"] + "/sequence-current.json")],
    )
    seq["originalLocations"] = [loc]
    original = (context.root / "transport" / f"{manifest['archiveSha256']}.zip").read_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as zin, zipfile.ZipFile(output, "w") as zout:
        for name in zin.namelist():
            zout.writestr(name, zin.read(name))
        zout.writestr(loc["archiveMemberChain"][0]["member"], seqraw)
    rebind_archive(root, registry, context, manifest, output.getvalue())
    for desc in [*plan["captureDescriptors"], *continuous["originalLocations"], loc]:
        desc["artifactZipSha256"] = manifest["archiveSha256"]
    dependencies = ()
    if order == "continuous-first":
        plan["receiptDescriptors"] = [continuous, seq]
    elif order in ("external-dependency", "foreign"):
        plan["receiptDescriptors"] = [seq]
        dependencies = [continuous]
        if order == "foreign":
            continuous["originalLocations"][0]["runId"] = "999"
    elif order == "missing":
        plan["receiptDescriptors"] = [seq]
    else:
        plan["receiptDescriptors"] = [seq, continuous]
    seen = []

    def inspect_staging(raw, path, family, version, provenance, repo):
        assert (path.parent / "sequence-current.json").is_file()
        assert (path.parent / "continuous-current.json").is_file()
        seen.append(family)

    monkeypatch.setattr(typed, "validate_receipt", inspect_staging)
    if order in ("missing", "foreign"):
        with pytest.raises(ValueError):
            local.derive_plan_binding(repo, plan, context, dependency_descriptors=dependencies)
    else:
        result = local.derive_plan_binding(repo, plan, context, dependency_descriptors=dependencies)
        assert result.project == manifest["project"]
        assert sorted(seen) == ["continuous", "sequence"]


@pytest.mark.parametrize(
    "fault", ["count", "frame-bytes", "metadata-bytes", "receipt-count", "negative", "boolean"]
)
def test_resource_preflight_has_no_filesystem_operations(local_bundle, monkeypatch, fault):
    import tempfile

    repo, _, _, context, manifest = local_bundle
    plan = dict(
        suite=manifest["suite"],
        case=manifest["case"],
        projectCandidates=[manifest["project"]],
        captureDescriptors=[],
        receiptDescriptors=[],
    )
    if fault == "count":
        plan["captureDescriptors"] = [{}] * 65537
    elif fault == "frame-bytes":
        plan["captureDescriptors"] = [dict(sizeBytes=32 * 1024**2)] * 193
    elif fault == "metadata-bytes":
        plan["receiptDescriptors"] = [dict(bytes=9 * 1024**2, sha256=c * 64) for c in ("a", "b")]
    elif fault == "receipt-count":
        plan["receiptDescriptors"] = [{}] * 257
    else:
        plan["captureDescriptors"] = [dict(sizeBytes=-1 if fault == "negative" else True)]

    def forbidden(*args, **kwargs):
        pytest.fail("filesystem before resource preflight")

    monkeypatch.setattr(a, "verify_source", forbidden)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", forbidden)
    with pytest.raises(ValueError, match="planned"):
        local.derive_plan_binding(repo, plan, context)


def test_existing_route_does_not_require_new_title_or_retry_errors(local_bundle, monkeypatch):
    repo, _, _, context, _ = local_bundle
    plan = binding_plan(local_bundle)
    plan["captureDescriptors"][0]["nativeTestBindingStatus"] = "unknown-not-inferred-from-filename"

    def forbidden(*args, **kwargs):
        pytest.fail("unsupported derivation fallback")

    monkeypatch.setattr(local, "derive_plan_binding", forbidden)
    assert local.select_plan_route(plan) == "existing-manifest"
    assert local.prepare_plan_manifests(repo, plan, context)[0]["originalOutcome"] == "unknown"
    plan["captureDescriptors"][0]["sha256"] = "invalid"
    with pytest.raises(ValueError):
        local.prepare_plan_manifests(repo, plan, context)


@pytest.mark.parametrize("empty,exact", [(True, False), (False, True), (True, True)])
def test_route_derives_only_for_missing_project_or_exact_title(local_bundle, empty, exact):
    plan = binding_plan(local_bundle)
    if empty:
        plan["projectCandidates"] = []
    if not exact:
        plan["captureDescriptors"][0]["nativeTestBindingStatus"] = (
            "unknown-not-inferred-from-filename"
        )
    assert local.select_plan_route(plan) == "derive-explicit-originals"


@pytest.mark.parametrize("reverse", [False, True])
def test_partial_identity_consistency_does_not_infer_title(local_bundle, reverse):
    plan = binding_plan(local_bundle)
    project = plan["projectCandidates"][0]
    title = plan["captureDescriptors"][0]["test"]
    originals = [dict(project=project), {}, dict(project=project, test=title)]
    if reverse:
        originals.reverse()
    assert local._consistent_receipt_identity(plan, originals) == (project, title)
    with pytest.raises(ValueError, match="unique explicit"):
        local._consistent_receipt_identity(plan, [dict(project=project), dict(test=title)])
    with pytest.raises(ValueError, match="conflicting partial"):
        local._consistent_receipt_identity(plan, originals + [dict(project="webkit-mobile")])
    with pytest.raises(ValueError, match="conflicting partial"):
        local._consistent_receipt_identity(plan, originals + [dict(test="wrong")])
    with pytest.raises(ValueError, match="conflicting original"):
        local._consistent_receipt_identity(
            plan, [dict(project=project, binding=dict(project="wrong"))]
        )
