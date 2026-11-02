"""Synthetic cross-part archival closure, not native or pixel acceptance."""

import copy
import json
from pathlib import Path

import pytest

from scripts.python import archive_support
from scripts.python import screenshot_archive as a
from scripts.python import typed_archive_support as typed
from scripts.tests.test_screenshot_archive import git, sample  # noqa: F401

CASE = "workspace-release-selected-9c572-aves-or-discards-explicitly-chromium-compact"


@pytest.fixture
def bundle(sample, tmp_path):  # noqa: F811
    import zipfile

    repo, zip_path, manifest = sample
    name = "current-continuous-current-000.png"
    with zipfile.ZipFile(zip_path) as z:
        png = z.read("case/actual.png")
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr(CASE + "/" + name, png)
    manifest["archiveSha256"] = a.digest(zip_path.read_bytes())
    frame = manifest["captures"][0]
    frame.update(
        member=CASE + "/" + name,
        project="chromium-compact",
        test="selected record editing stays contained and saves or discards explicitly",
    )
    path = a.import_archive(repo, zip_path, manifest)
    raw_manifest = path.read_bytes()
    receipt = dict(
        schemaVersion=1,
        scope="synthetic-workspace-ownership",
        scenario="selected",
        sourceCommit=manifest["sourceCommit"],
        sourceTree=manifest["sourceTree"],
        runId="11",
        attempt="1",
        revoked=True,
        bodySettled=True,
        hookStarted=True,
        incomplete=True,
        coverage={
            s: "incomplete"
            for s in (
                "workspace-records-selected-edit",
                "workspace-records-selected-saved",
                "current",
            )
        },
        errors=["body-failed", "coverage-incomplete"],
        frames=[dict(file=name, sha256=a.digest(png), bytes=len(png))],
    )
    raw = json.dumps(receipt).encode()
    digest = a.digest(raw)
    root = tmp_path / "supplied"
    (root / "objects").mkdir(parents=True)
    (root / "objects" / f"{digest}.json").write_bytes(raw)
    member = CASE + "/workspace-capture-ownership.json"
    entry = dict(
        path=f"objects/{digest}.json",
        sha256=digest,
        bytes=len(raw),
        family="ownership",
        schemaVersion=1,
        artifactId=33,
        archiveSha256=manifest["archiveSha256"],
        member=member,
        archiveChain=[
            dict(member=member, sha256=digest, hashBasis="externally-verified-original-member")
        ],
    )
    row = {
        k: manifest[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    row.update(
        suite="workspace",
        case=CASE,
        project="chromium-compact",
        manifests=[
            dict(
                path=path.relative_to(repo / "evidence/visual").as_posix(),
                sha256=a.digest(raw_manifest),
            )
        ],
        receipts=[entry],
    )
    return repo, root, dict(schemaVersion=2, kind="typed-diagnostic-support", bundles=[row])


def test_original_partial_retained_and_second_import_changes_no_source(bundle):
    repo, root, registry = bundle
    raw = json.dumps(registry).encode()
    catalog = archive_support.CATALOG_PATH.read_bytes()
    before = git(repo, "status", "--short")
    name = typed.register(repo, raw, root)
    original = (repo / "evidence/visual/support" / name).read_bytes()
    assert original == raw
    assert typed.register(repo, raw, root) == name
    assert archive_support.CATALOG_PATH.read_bytes() == catalog
    archive_support.validate_support(repo)
    assert git(repo, "status", "--short") == before
    assert len(list((repo / "evidence/visual/objects").glob("*.png"))) == 1


@pytest.mark.parametrize(
    "fault",
    [
        "missing-frame",
        "wrong-run",
        "wrong-project",
        "unknown-producer",
        "duplicate-receipt",
        "unknown-family",
        "unknown-version",
        "unknown-field",
        "wrong-manifest",
        "extra-manifest",
    ],
)
def test_rejects_unbound_or_unknown_payloads_before_any_write(bundle, fault):
    repo, root, d = bundle
    b = d["bundles"][0]
    if fault == "missing-frame":
        next((repo / "evidence/visual/objects").glob("*.png")).unlink()
    elif fault == "wrong-run":
        b["runId"] += 1
    elif fault == "wrong-project":
        b["project"] = "chromium-desktop"
    elif fault == "unknown-producer":
        b["case"] = "private"
    elif fault == "duplicate-receipt":
        b["receipts"].append(copy.deepcopy(b["receipts"][0]))
    elif fault == "unknown-family":
        b["receipts"][0]["family"] = "movement"
    elif fault == "unknown-version":
        b["receipts"][0]["schemaVersion"] = 999
    elif fault == "unknown-field":
        b["private"] = "excluded"
    elif fault == "wrong-manifest":
        b["manifests"][0]["sha256"] = "0" * 64
    else:
        b["manifests"].append(copy.deepcopy(b["manifests"][0]))
    with pytest.raises((ValueError, FileNotFoundError)):
        typed.register(repo, json.dumps(d).encode(), root)
    assert not (repo / "evidence/visual/support").exists()


def test_duplicate_keys_rejected_before_registration(bundle):
    repo, root, d = bundle
    raw = (
        json.dumps(d)
        .encode()
        .replace(b'"schemaVersion": 2', b'"schemaVersion": 2,"schemaVersion": 2', 1)
    )
    with pytest.raises(ValueError, match="duplicate"):
        typed.register(repo, raw, root)


def test_native_envelopes_and_movement_are_not_fabricated_receipts(bundle):
    repo, root, d = bundle
    for family in ("movement", "native-provenance", "source-after"):
        d["bundles"][0]["receipts"][0]["family"] = family
        with pytest.raises(ValueError, match="family/version"):
            typed.register(repo, json.dumps(d).encode(), root)


@pytest.mark.parametrize("version", [1, 2])
def test_confirmation_capture_aware_version_requires_endpoint_closure(bundle, version):
    repo, root, d = bundle
    b = d["bundles"][0]
    original_entry = b["receipts"][0]
    receipt = json.loads((root / original_entry["path"]).read_bytes())
    case = "workspace-release-workspac-c3eae-ons-cancel-without-mutation-chromium-desktop"
    b.update(case=case, project="chromium-desktop")
    receipt.update(schemaVersion=version, scenario="confirmations", incomplete=False, errors=[])
    states = ["workspace-confirm-" + s for s in ["submit-review", "publish", "delete", "restore"]]
    receipt["coverage"] = {s: "complete" for s in states + ["current"]}
    prototype = receipt["frames"][0]
    receipt["frames"] = [dict(prototype, file=s + "-attempt.png") for s in states]
    manifest_path = repo / "evidence/visual" / b["manifests"][0]["path"]
    manifest = json.loads(manifest_path.read_bytes())
    capture = manifest["captures"][0]
    manifest["captures"] = [
        dict(
            capture,
            member=case + "/" + f["file"],
            project="chromium-desktop",
            test="workspace workflow confirmations cancel without mutation",
        )
        for f in receipt["frames"]
    ]
    manifest_raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(manifest_raw)
    b["manifests"][0]["sha256"] = a.digest(manifest_raw)
    raw = json.dumps(receipt).encode()
    digest = a.digest(raw)
    (root / "objects" / f"{digest}.json").write_bytes(raw)
    member = case + "/workspace-capture-ownership.json"
    b["receipts"] = [
        dict(
            original_entry,
            path=f"objects/{digest}.json",
            sha256=digest,
            bytes=len(raw),
            schemaVersion=version,
            member=member,
            archiveChain=[
                dict(member=member, sha256=digest, hashBasis="externally-verified-original-member")
            ],
        )
    ]
    if version == 1:
        # Historical claims are retained as original v1, never upgraded to endpoints.
        assert typed.validate_registry(repo, d, root)
    else:
        with pytest.raises(ValueError, match="ownership"):
            typed.validate_registry(repo, d, root)
    assert not (repo / "evidence/visual/support").exists()


def test_cross_part_frame_ambiguity_is_fatal(bundle):
    import io

    from PIL import Image

    repo, root, d = bundle
    b = d["bundles"][0]
    first = repo / "evidence/visual" / b["manifests"][0]["path"]
    manifest = json.loads(first.read_bytes())
    buf = io.BytesIO()
    Image.new("RGB", (2, 3), "white").save(buf, format="PNG")
    raw = buf.getvalue()
    digest = a.digest(raw)
    (repo / "evidence/visual/objects" / f"{digest}.png").write_bytes(raw)
    manifest["artifactId"] = 44
    manifest["captures"][0].update(sha256=digest, bytes=len(raw), storage=f"objects/{digest}.png")
    other = first.with_name("11-1-22-44.json")
    other.write_text(json.dumps(manifest))
    b["manifests"].append(
        dict(
            path=other.relative_to(repo / "evidence/visual").as_posix(),
            sha256=a.digest(other.read_bytes()),
        )
    )
    with pytest.raises(ValueError, match="ambiguous cross-part"):
        typed.validate_registry(repo, d, root)


@pytest.fixture
def checkpoint_bundle(sample, tmp_path):  # noqa: F811
    import zipfile

    from scripts.tests.test_native_archive_evidence import current_shell_provenance

    repo, zip_path, manifest = sample
    case = "workspace-release-workspac-92e7c-ponsive-and-visually-stable-webkit-mobile"
    title = "workspace records and schema are accessible, responsive, and visually stable"
    name = "current-continuous-current-000.png"
    with zipfile.ZipFile(zip_path) as z:
        image = z.read("case/actual.png")
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr(case + "/" + name, image)
    manifest["archiveSha256"] = a.digest(zip_path.read_bytes())
    manifest["captures"][0].update(member=case + "/" + name, project="webkit-mobile", test=title)
    manifest_path = a.import_archive(repo, zip_path, manifest)
    root = tmp_path / "checkpoint-supplied"
    (root / "objects").mkdir(parents=True)
    raw = json.dumps(
        dict(schemaVersion=1, scope="synthetic-workspace-webkit", incomplete=True, events=[])
    ).encode()

    def descriptor(raw, member):
        sha = a.digest(raw)
        (root / "objects" / (sha + ".json")).write_bytes(raw)
        return dict(
            path=f"objects/{sha}.json",
            sha256=sha,
            bytes=len(raw),
            artifactId=33,
            archiveSha256=manifest["archiveSha256"],
            member=member,
            archiveChain=[
                dict(member=member, sha256=sha, hashBasis="externally-verified-original-member")
            ],
        )

    receipt = descriptor(raw, "workspace/" + case + "/workspace-scroll-checkpoints.json")
    receipt.update(family="checkpoint", schemaVersion=1)
    envelope = current_shell_provenance()
    envelope.update(
        {
            k: str(manifest[k])
            for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
        }
    )
    envelope["diagnosticReceiptCount"] = 1
    envelope["diagnostics"] = [
        dict(
            path=receipt["member"],
            bytes=len(raw),
            sha256=a.digest(raw),
            sourceRoot="workspace",
            role="workspace-phase-diagnostic",
        )
    ]
    env_entry = descriptor(json.dumps(envelope).encode(), "provenance.json")
    row = {
        k: manifest[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    row.update(
        suite="workspace",
        case=case,
        project="webkit-mobile",
        manifests=[
            dict(
                path=manifest_path.relative_to(repo / "evidence/visual").as_posix(),
                sha256=a.digest(manifest_path.read_bytes()),
            )
        ],
        receipts=[receipt],
        nativeEnvelopes=[env_entry],
    )
    return repo, root, dict(schemaVersion=2, kind="typed-diagnostic-support", bundles=[row])


def test_checkpoint_registration_requires_source_bound_native_envelope(checkpoint_bundle):
    repo, root, registry = checkpoint_bundle
    paths = typed.validate_registry(repo, registry, root)
    assert len(paths) == 2
    # An incomplete checkpoint is retained as such; it certifies no screenshot.
    path = typed.register(repo, json.dumps(registry).encode(), root)
    assert typed.register(repo, json.dumps(registry).encode(), root) == path


@pytest.mark.parametrize(
    "fault", ["missing", "archive", "artifact", "source", "descriptor", "extra", "duplicate"]
)
def test_checkpoint_registration_rejects_broken_native_binding(checkpoint_bundle, fault):
    repo, root, registry = checkpoint_bundle
    row = registry["bundles"][0]
    env = row["nativeEnvelopes"][0]
    if fault == "missing":
        row["nativeEnvelopes"] = []
    elif fault == "archive":
        env["archiveSha256"] = "f" * 64
    elif fault == "artifact":
        env["artifactId"] += 1
    elif fault == "extra":
        env["ignored"] = True
    elif fault == "duplicate":
        row["nativeEnvelopes"] *= 2
    else:
        data = json.loads((root / env["path"]).read_bytes())
        if fault == "source":
            data["sourceCommit"] = "e" * 40
        else:
            data["diagnostics"][0]["sha256"] = "f" * 64
        raw = json.dumps(data).encode()
        sha = a.digest(raw)
        env.update(path=f"objects/{sha}.json", sha256=sha, bytes=len(raw))
        env["archiveChain"][-1]["sha256"] = sha
        (root / env["path"]).write_bytes(raw)
    with pytest.raises(ValueError):
        typed.validate_registry(repo, registry, root)


def test_media_geometry_requires_every_corresponding_decodable_png(tmp_path):
    import io

    from PIL import Image

    from scripts.tests.test_visual_matrix_artifacts import media_observation_fixture

    _, case, _, path, _ = media_observation_fixture(tmp_path)
    row = dict(
        suite="media",
        case=case.name,
        project="chromium-desktop",
        sourceCommit="a" * 40,
        sourceTree="b" * 40,
        runId=123,
        attempt=1,
    )
    stream = io.BytesIO()
    Image.new("RGB", (2, 3)).save(stream, format="PNG")
    png = stream.getvalue()
    for index in (0, 2, 4):
        (case / f"current-media-library-viewport-{index}.png").write_bytes(png)
    assert typed.validate_receipt(path.read_bytes(), path, "media-geometry", 1, row, tmp_path)
    (case / "current-media-library-viewport-2.png").unlink()
    with pytest.raises(ValueError, match="missing corresponding"):
        typed.validate_receipt(path.read_bytes(), path, "media-geometry", 1, row, tmp_path)
    (case / "current-media-library-viewport-2.png").write_bytes(b"invalid PNG")
    with pytest.raises(ValueError):
        typed.validate_receipt(path.read_bytes(), path, "media-geometry", 1, row, tmp_path)


def test_inventory_binding_requires_exact_part_hash_and_diagnostic_identity():
    entry = dict(
        member="case/media-viewport-observations.json",
        family="media-geometry",
        bytes=100,
        sha256="a" * 64,
        archiveChain=[
            dict(member="chromium-desktop-part-0.zip", sha256="b" * 64),
            dict(member="case/media-viewport-observations.json", sha256="a" * 64),
        ],
    )
    envelope = dict(member="inventory.json")
    data = dict(
        projects={
            "chromium-desktop": dict(
                diagnostics=[
                    dict(
                        path=entry["member"],
                        bytes=100,
                        sha256="a" * 64,
                        archive="chromium-desktop-part-0.zip",
                    )
                ],
                parts=[dict(path="chromium-desktop-part-0.zip", sha256="b" * 64)],
            )
        }
    )
    typed.native_envelope_binding(entry, envelope, data)
    entry["archiveChain"][0]["sha256"] = "c" * 64
    with pytest.raises(ValueError, match="part binding"):
        typed.native_envelope_binding(entry, envelope, data)


def test_native_geometry_envelope_cannot_bind_different_producer_image_bytes():
    image = b"checked elsewhere as PNG"
    member = "case/media-viewport-observations.json"
    entry = dict(
        member=member,
        family="media-geometry",
        bytes=100,
        sha256="a" * 64,
        archiveChain=[
            dict(member="chromium-desktop.zip", sha256="b" * 64),
            dict(member=member, sha256="a" * 64),
        ],
    )
    envelope = dict(member="inventory.json")
    data = dict(
        projects={
            "chromium-desktop": dict(
                diagnostics=[
                    dict(path=member, bytes=100, sha256="a" * 64, archive="chromium-desktop.zip")
                ],
                parts=[dict(path="chromium-desktop.zip", sha256="b" * 64)],
                captures=[
                    dict(
                        path="case/current-media-library-viewport-0.png",
                        bytes=len(image),
                        sha256=a.digest(image),
                    )
                ],
            )
        }
    )
    frames = {"current-media-library-viewport-0.png": image}
    typed.native_envelope_binding(entry, envelope, data, frames)
    with pytest.raises(ValueError, match="frame identity"):
        typed.native_envelope_binding(entry, envelope, data, {})
    with pytest.raises(ValueError, match="frame identity"):
        typed.native_envelope_binding(
            entry, envelope, data, {"current-media-library-viewport-0.png": b"different"}
        )


@pytest.mark.parametrize(
    "suite,case,project,title",
    [
        (
            "volcano",
            "volcano-preservation-Volca-771ea-icated-route-admin-at-390px-chromium",
            "chromium",
            "Volcano authenticated route /admin at 390px",
        ),
        (
            "journeys",
            "public-journeys-public-jou-844ca-nd-retry-sends-exactly-once-chromium",
            "chromium",
            "contact missing service fails visibly and retry sends exactly once",
        ),
    ],
)
def test_exact_observed_standard_producer_mapping(suite, case, project, title):
    assert typed.producer_title(suite, case, project) == title
    assert typed.producer_title("operations", case, project) is None
    assert typed.producer_title(suite, case + "-extra", project) is None
    assert typed.producer_title(suite, case, "unknown") is None


def test_unregistered_width_and_layout_png_do_not_become_typed_producers():
    assert (
        typed.producer_title(
            "journeys",
            "public-journeys-public-jou-2bd68-nd-retry-sends-exactly-once-chromium",
            "chromium",
        )
        is None
    )
    assert typed.producer_title("layout", "representative--at-1024px-chromium", "chromium") is None
    assert (
        typed.producer_title(
            "unknown", "operations-release-anything-chromium-desktop", "chromium-desktop"
        )
        is None
    )


@pytest.fixture
def report_dependencies(tmp_path):
    from scripts.tests.test_native_archive_evidence import PROVENANCE, before

    raw = json.dumps(before()).encode()
    sha = a.digest(raw)
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / f"{sha}.json").write_bytes(raw)
    envelope = dict(
        member="inventory.json",
        artifactId=10,
        archiveSha256="c" * 64,
        archiveChain=[
            dict(
                member="inventory.json",
                sha256="d" * 64,
                hashBasis="externally-verified-original-member",
            )
        ],
    )
    data = dict(originalReports=[dict(path="source-before.json", bytes=len(raw), sha256=sha)])
    entry = dict(
        path=f"objects/{sha}.json",
        sha256=sha,
        bytes=len(raw),
        artifactId=10,
        archiveSha256="c" * 64,
        member="source-before.json",
        archiveChain=[
            dict(
                member="source-before.json",
                sha256=sha,
                hashBasis="externally-verified-original-member",
            )
        ],
    )
    return tmp_path, PROVENANCE, [(envelope, data)], [entry]


def test_inventory_original_report_dependencies_preserve_exact_bytes(report_dependencies):
    root, bundle, envelopes, entries = report_dependencies
    assert typed.load_native_reports(entries, envelopes, bundle, root) == {entries[0]["path"]}


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "duplicate", "archive", "container", "leaf", "changed", "source"]
)
def test_inventory_original_reports_cannot_be_omitted_or_rebound(report_dependencies, fault):
    root, bundle, envelopes, entries = report_dependencies
    if fault == "missing":
        entries = []
    elif fault == "extra":
        entries[0]["member"] = "other.json"
    elif fault == "duplicate":
        entries *= 2
    elif fault == "archive":
        entries[0]["artifactId"] = 99
    elif fault == "container":
        entries[0]["archiveChain"].insert(
            0,
            dict(
                member="other.zip", sha256="e" * 64, hashBasis="externally-verified-original-member"
            ),
        )
    elif fault == "leaf":
        entries[0]["archiveChain"][-1]["sha256"] = "e" * 64
    elif fault == "changed":
        (root / entries[0]["path"]).write_bytes(b"changed")
    elif fault == "source":
        bundle = dict(bundle, sourceCommit="f" * 40)
    with pytest.raises(ValueError):
        typed.load_native_reports(entries, envelopes, bundle, root)


def test_media_geometry_full_registration_closes_reports_parts_and_viewport_images(
    sample,  # noqa: F811
    tmp_path,
):
    import io
    import zipfile

    from PIL import Image

    from scripts.tests.test_native_archive_evidence import after, before
    from scripts.tests.test_visual_matrix_artifacts import media_observation_fixture

    repo, zip_path, manifest = sample
    fixture_root = tmp_path / "media"
    fixture_root.mkdir()
    _, case, _, observation, _ = media_observation_fixture(fixture_root)
    title = "media library is accessible responsive and visually reviewed"
    project = "chromium-desktop"
    stream = io.BytesIO()
    Image.new("RGB", (2, 3)).save(stream, format="PNG")
    png = stream.getvalue()
    captures = []
    with zipfile.ZipFile(zip_path, "w") as z:
        for index in (0, 2, 4):
            row = copy.deepcopy(manifest["captures"][0])
            row.update(
                member=case.name + f"/current-media-library-viewport-{index}.png",
                project=project,
                test=title,
                sha256=a.digest(png),
                bytes=len(png),
                dimensions=[2, 3],
                storage=f"objects/{a.digest(png)}.png",
            )
            captures.append(row)
            z.writestr(row["member"], png)
    manifest.update(captures=captures, archiveSha256=a.digest(zip_path.read_bytes()))
    mpath = a.import_archive(repo, zip_path, manifest)
    root = tmp_path / "supplied-media"
    (root / "objects").mkdir(parents=True)
    raw = observation.read_bytes()
    part = "chromium-desktop.zip"
    partsha = manifest["archiveSha256"]

    def desc(body, member, chain=None):
        sha = a.digest(body)
        (root / "objects" / f"{sha}.json").write_bytes(body)
        return dict(
            path=f"objects/{sha}.json",
            sha256=sha,
            bytes=len(body),
            artifactId=33,
            archiveSha256="e" * 64,
            member=member,
            archiveChain=(chain or [])
            + [dict(member=member, sha256=sha, hashBasis="externally-verified-original-member")],
        )

    receipt = desc(
        raw,
        case.name + "/media-viewport-observations.json",
        [dict(member=part, sha256=partsha, hashBasis="externally-verified-original-member")],
    )
    receipt.update(family="media-geometry", schemaVersion=1)
    identity = {k: str(manifest[k]) for k in ("sourceCommit", "sourceTree", "runId", "attempt")}
    b = before()
    b.update(identity, matrix="media")
    b["expectedTests"][0]["title"] = title
    aft = after()
    aft.update(
        {k: v for k, v in identity.items() if k != "sourceTree"},
        matrix="media",
        sourceGuardErrors=[],
    )
    aft["tests"][0]["title"] = title
    reports = [
        desc(json.dumps(value).encode(), name)
        for value, name in [(b, "source-before.json"), (aft, "source-after.json")]
    ]
    inv = dict(
        schemaVersion=2,
        **identity,
        matrix="media",
        scope="Diagnostic packaging only; empty/missing captures are incomplete, not acceptance.",
        originalReports=[
            dict(path=r["member"], bytes=r["bytes"], sha256=r["sha256"]) for r in reports
        ],
        missingReports=["operations-visual-runner.json", "stages.md"],
        errors=[],
        complete=False,
        projects={
            project: dict(
                status="packaged",
                expectedSupportedTests=b["expectedTests"],
                currentCaptureCount=3,
                minimumCaptureShortfall=0,
                captureCoverage="requires-review",
                missingDiagnostics=[],
                captures=[
                    dict(path=c["member"], bytes=c["bytes"], sha256=c["sha256"], archive=part)
                    for c in captures
                ],
                diagnostics=[
                    dict(path=receipt["member"], bytes=len(raw), sha256=a.digest(raw), archive=part)
                ],
                parts=[
                    dict(
                        path=part,
                        bytes=100,
                        sha256=partsha,
                        members=[c["member"] for c in captures] + [receipt["member"]],
                    )
                ],
            )
        },
    )
    envelope = desc(json.dumps(inv).encode(), "inventory.json")
    row = {
        k: manifest[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    row.update(
        suite="media",
        case=case.name,
        project=project,
        manifests=[
            dict(
                path=mpath.relative_to(repo / "evidence/visual").as_posix(),
                sha256=a.digest(mpath.read_bytes()),
            )
        ],
        receipts=[receipt],
        nativeEnvelopes=[envelope],
        nativeReports=reports,
    )
    registry = dict(schemaVersion=2, kind="typed-diagnostic-support", bundles=[row])
    assert len(typed.validate_registry(repo, registry, root)) == 4
    row["nativeReports"] = reports[:1]
    with pytest.raises(ValueError, match="missing native report dependency"):
        typed.validate_registry(repo, registry, root)


def test_support_batch_cap_counts_envelopes_and_reports_before_reading(bundle):
    repo, root, registry = bundle
    row = registry["bundles"][0]
    row["nativeEnvelopes"] = [dict(path="objects/" + "a" * 64 + ".json", bytes=typed.MAX_BYTES)]
    with pytest.raises(ValueError, match="support batch byte bound"):
        typed.validate_registry(repo, registry, root)


def test_support_batch_cap_is_global_not_reset_per_bundle(bundle):
    repo, root, registry = bundle
    registry["bundles"].append(copy.deepcopy(registry["bundles"][0]))
    for index, row in enumerate(registry["bundles"]):
        row["receipts"][0].update(
            path="objects/" + str(index) * 64 + ".json", bytes=typed.MAX_BYTES // 2 + 1
        )
    with pytest.raises(ValueError, match="support batch byte bound"):
        typed.validate_registry(repo, registry, root)


@pytest.mark.parametrize("prefix", ["", "00/"])
def test_provenance_geometry_exact_container_prefix_and_frames(prefix):
    case = "media-release-media-librar-1b4ce-nsive-and-visually-reviewed-chromium-high-contrast"
    relative = f"media_hc/{case}/media-viewport-observations.json"
    container = [dict(member="metadata.zip", sha256="c" * 64)]
    envelope = dict(
        member=prefix + "provenance.json",
        artifactId=9,
        archiveSha256="b" * 64,
        archiveChain=container + [dict(member=prefix + "provenance.json")],
    )
    entry = dict(
        member=prefix + relative,
        artifactId=9,
        archiveSha256="b" * 64,
        archiveChain=container + [dict(member=prefix + relative)],
        family="media-geometry",
        bytes=10,
        sha256="a" * 64,
    )
    body = b"synthetic image identity only"
    data = dict(
        diagnostics=[
            dict(path=relative, role="media-viewport-diagnostic", bytes=10, sha256="a" * 64)
        ],
        captures=[
            dict(
                path=f"media_hc/{case}/current-media-library-viewport-0.png",
                sourceRoot="media_hc",
                bytes=len(body),
                sha256=typed.a.digest(body),
            )
        ],
    )
    frames = {"current-media-library-viewport-0.png": body}
    typed.native_envelope_binding(entry, envelope, data, frames)
    for fault in ["container", "prefix", "artifact", "digest", "missing", "source"]:
        import copy

        bad, env, payload = copy.deepcopy(entry), copy.deepcopy(envelope), copy.deepcopy(data)
        images = dict(frames)
        if fault == "container":
            bad["archiveChain"][0]["sha256"] = "d" * 64
        elif fault == "prefix":
            env["member"] = "other/provenance.json"
        elif fault == "artifact":
            bad["artifactId"] = 10
        elif fault == "digest":
            payload["captures"][0]["sha256"] = "e" * 64
        elif fault == "missing":
            images = {}
        else:
            payload["captures"][0]["sourceRoot"] = "operations_hc"
        with pytest.raises(ValueError):
            typed.native_envelope_binding(bad, env, payload, images)


def test_hash_only_historical_registry_keeps_scope_and_second_import_stable(checkpoint_bundle):
    from scripts.python.native_archive_evidence import HASH_ONLY_SCOPE

    repo, root, registry = checkpoint_bundle
    row = registry["bundles"][0]
    envelope = row["nativeEnvelopes"][0]
    old = json.loads((root / envelope["path"]).read_bytes())
    old["scope"] = HASH_ONLY_SCOPE
    raw = json.dumps(old).encode()
    sha = a.digest(raw)
    envelope.update(path=f"objects/{sha}.json", sha256=sha, bytes=len(raw))
    envelope["archiveChain"][-1]["sha256"] = sha
    (root / envelope["path"]).write_bytes(raw)
    catalog = archive_support.CATALOG_PATH.read_bytes()
    name = typed.register(repo, json.dumps(registry).encode(), root)
    status = git(repo, "status", "--short")
    assert typed.register(repo, json.dumps(registry).encode(), root) == name
    assert git(repo, "status", "--short") == status
    assert archive_support.CATALOG_PATH.read_bytes() == catalog
    assert (repo / "evidence/visual/support" / envelope["path"]).read_bytes() == raw
    assert json.loads(raw)["scope"] == HASH_ONLY_SCOPE


@pytest.mark.parametrize("fault", ["tree", "unrelated-history", "retained-proof"])
def test_registry_source_dag_is_checked_before_retention(bundle, fault):
    import subprocess

    repo, root, registry = bundle
    row = registry["bundles"][0]
    if fault == "tree":
        row["sourceTree"] = "f" * 40
    elif fault == "unrelated-history":
        # A real commit with the same tree but no parent is not an ancestor.
        orphan = subprocess.check_output(
            ["git", "commit-tree", row["sourceTree"], "-m", "unrelated"], cwd=repo, text=True
        ).strip()
        row["requestedHead"] = orphan
    else:
        path = repo / "evidence/visual/sources" / f"{row['sourceCommit']}.commit"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"not the original Git commit")
    before = (
        set((repo / "evidence/visual/support").rglob("*"))
        if (repo / "evidence/visual/support").exists()
        else set()
    )
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        typed.register(repo, json.dumps(registry).encode(), root)
    after = (
        set((repo / "evidence/visual/support").rglob("*"))
        if (repo / "evidence/visual/support").exists()
        else set()
    )
    assert before == after


@pytest.fixture
def quarantine_bundle(sample, tmp_path):  # noqa: F811
    from scripts.tests.test_native_archive_evidence import inventory

    repo, _, manifest = sample
    identity = {
        k: manifest[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    data = inventory()
    data.update({k: str(v) for k, v in identity.items() if k != "requestedHead"}, complete=True)
    raw = json.dumps(data).encode()
    sha = a.digest(raw)
    root = tmp_path / "quarantine-supplied"
    path = f"quarantine/objects/{sha}.json"
    (root / path).parent.mkdir(parents=True)
    (root / path).write_bytes(raw)
    entry = dict(
        identity,
        contradictions=["complete-with-missing-reports"],
        object=dict(
            path=path,
            sha256=sha,
            bytes=len(raw),
            artifactId=33,
            archiveSha256="d" * 64,
            member="metadata/inventory.json",
            archiveChain=[
                dict(
                    member="metadata/inventory.json",
                    sha256=sha,
                    hashBasis="externally-verified-original-member",
                )
            ],
        ),
    )
    registry = dict(
        schemaVersion=3,
        kind="quarantined-native-diagnostics",
        acceptance=False,
        closure=False,
        entries=[entry],
    )
    return repo, root, registry, raw


def test_quarantine_retention_is_data_only_immutable_and_not_proof(quarantine_bundle):
    from scripts.python import native_archive_evidence as native

    repo, root, registry, original = quarantine_bundle
    catalog = archive_support.CATALOG_PATH.read_bytes()
    source_tree = git(repo, "rev-parse", "HEAD^{tree}")
    tracked = {p: (repo / p).read_bytes() for p in git(repo, "ls-files").splitlines()}
    raw = json.dumps(registry).encode()
    path = typed.register_quarantine(repo, raw, root)
    archive_support.validate_support(repo)
    target = repo / "evidence/visual/support" / registry["entries"][0]["object"]["path"]
    assert target.read_bytes() == original
    assert json.loads(original)["complete"] is True
    assert json.loads(original)["missingReports"]
    before = {
        str(p): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in (repo / "evidence/visual/support").rglob("*")
        if p.is_file()
    }
    assert typed.register_quarantine(repo, raw, root) == path
    assert before == {
        str(p): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in (repo / "evidence/visual/support").rglob("*")
        if p.is_file()
    }
    assert git(repo, "rev-parse", "HEAD^{tree}") == source_tree
    assert tracked == {p: (repo / p).read_bytes() for p in tracked}
    assert archive_support.CATALOG_PATH.read_bytes() == catalog
    assert not (repo / "evidence/visual/objects").exists()  # No PNG import, even in this fixture.
    assert not (repo / "evidence/visual/support/objects").exists()
    with pytest.raises(ValueError):
        typed.validate_registry(repo, registry)
    with pytest.raises(ValueError, match="complete reports contradiction"):
        native.validate_inventory_objects(original, registry["entries"][0], {})


@pytest.mark.parametrize(
    "fault",
    [
        "acceptance",
        "closure",
        "reason",
        "source",
        "hash",
        "chain",
        "family",
        "namespace",
        "duplicate",
        "extra",
    ],
)
def test_quarantine_rejects_invalid_binding_without_writes(quarantine_bundle, fault):
    repo, root, registry, _ = quarantine_bundle
    e = registry["entries"][0]
    obj = e["object"]
    if fault in ("acceptance", "closure"):
        registry[fault] = True
    elif fault == "reason":
        e["contradictions"] = []
    elif fault == "source":
        e["sourceTree"] = "f" * 40
    elif fault == "hash":
        (root / obj["path"]).write_bytes(b"{}")
    elif fault == "chain":
        obj["archiveChain"][-1]["sha256"] = "a" * 64
    elif fault == "family":
        obj["member"] = "provenance.json"
    elif fault == "namespace":
        obj["path"] = f"objects/{obj['sha256']}.json"
    elif fault == "duplicate":
        registry["entries"] *= 2
    else:
        registry["pass"] = True
    with pytest.raises(ValueError):
        typed.register_quarantine(repo, json.dumps(registry).encode(), root)
    assert not (repo / "evidence/visual/support").exists()


def test_quarantine_cannot_retain_valid_inventory_as_contradiction(quarantine_bundle):
    repo, root, registry, raw = quarantine_bundle
    data = json.loads(raw)
    data["complete"] = False
    raw = json.dumps(data).encode()
    sha = a.digest(raw)
    obj = registry["entries"][0]["object"]
    obj.update(path=f"quarantine/objects/{sha}.json", sha256=sha, bytes=len(raw))
    obj["archiveChain"][-1]["sha256"] = sha
    (root / obj["path"]).write_bytes(raw)
    with pytest.raises(ValueError, match="classification mismatch"):
        typed.register_quarantine(repo, json.dumps(registry).encode(), root)


@pytest.mark.parametrize("profile", ["aggregate", "pairs"])
def test_hc_view_local_zip_is_bound_to_source_and_exact_container(sample, profile):  # noqa: F811
    import io
    import zipfile

    from scripts.python import native_archive_evidence as native
    from scripts.tests.test_native_archive_evidence import legacy_hc

    repo, _, _ = sample
    source = repo / "scripts/python/workspace_png_evidence.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(
        (Path(__file__).parent / "fixtures/historical_hc" / (profile + ".txt")).read_bytes()
    )
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
        "pinned producer",
    )
    commit = git(repo, "rev-parse", "HEAD")
    data = legacy_hc()
    data.update(
        sourceCommit=commit, sourceTree=git(repo, "rev-parse", "HEAD^{tree}"), requestedHead=commit
    )
    png = (repo / "react-app/e2e/unit.spec.ts-snapshots/unit.png").read_bytes()
    name = "workspace-schema-post-assert.png"
    data["captures"] = [
        dict(
            path=native.hc_case(profile, "schema") + "/" + name,
            bytes=len(png),
            sha256=a.digest(png),
        )
    ]

    def make(value, member=name, image=png):
        raw = json.dumps(value).encode()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("provenance.json", raw)
            z.writestr(member, image)
        body = stream.getvalue()
        return body, dict(
            artifactId=33,
            archiveSha256=a.digest(body),
            member="provenance.json",
            sha256=a.digest(raw),
            bytes=len(raw),
        )

    body, descriptor = make(data)
    result = native.validate_hc_view_archive(repo, body, descriptor, data)
    assert result["originalOutcome"] == "failure"
    assert result["acceptance"] is False and result["runComplete"] is False
    assert result["dimensions"] == {data["captures"][0]["path"]: [2, 3]}
    # Working checkout content cannot replace historical producer declarations.
    source.write_text('CASE = "untrusted current source"\n')
    assert native.validate_hc_view_archive(repo, body, descriptor, data) == result
    with pytest.raises(ValueError, match="archive binding"):
        native.validate_hc_view_archive(repo, body + b"x", descriptor, data)
    for badbody, baddesc in [make(data, member="other/" + name), make(data, image=png + b"x")]:
        with pytest.raises(ValueError):
            native.validate_hc_view_archive(repo, badbody, baddesc, data)
    wrong = copy.deepcopy(data)
    wrong["captures"][0]["path"] = (
        native.hc_case("pairs" if profile == "aggregate" else "aggregate", "schema") + "/" + name
    )
    badbody, baddesc = make(wrong)
    with pytest.raises(ValueError, match="source-pinned view producer"):
        native.validate_hc_view_archive(repo, badbody, baddesc, data)


@pytest.mark.parametrize(
    "mutation",
    [
        "CASE: str = 'different-real-producer'",
        "CASE += 'different'",
        "CASES['schema'] = 'different'",
        "del VIEWS",
        "if True:\n    CASE = 'different'",
        "def hidden():\n    global CASE\n    CASE = 'different'",
        "CASES.update({'schema': 'different'})",
        "alias = CASES\nalias.clear()",
        "VIEWS = ('different',)",
        "for CASE in ('different',):\n    pass",
        "(CASE := 'different')",
    ],
)
def test_hc_rejects_all_unreviewed_producer_mutations(sample, mutation):  # noqa: F811
    from scripts.python import native_archive_evidence as native

    repo, _, _ = sample
    source = repo / "scripts/python/workspace_png_evidence.py"
    source.parent.mkdir(parents=True)
    original = (Path(__file__).parent / "fixtures/historical_hc/pairs.txt").read_bytes()
    source.write_bytes(original + b"\n" + mutation.encode() + b"\n")
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
        "mutation",
    )
    commit = git(repo, "rev-parse", "HEAD")
    provenance = dict(
        sourceCommit=commit,
        requestedHead=commit,
        sourceTree=git(repo, "rev-parse", "HEAD^{tree}"),
        runId=1,
        attempt=1,
    )
    with pytest.raises(ValueError):
        native.hc_source_profile(repo, provenance, "schema")


@pytest.fixture(params=[False, True])
def external_bundle(sample, tmp_path, request):  # noqa: F811
    import io
    import zipfile

    from scripts.tests.test_native_archive_evidence import PROJECT, inventory

    repo, _, manifest = sample
    identity = {
        k: manifest[k] for k in ("sourceCommit", "sourceTree", "requestedHead", "runId", "attempt")
    }
    data = inventory()
    data.update({k: str(v) for k, v in identity.items() if k != "requestedHead"}, schemaVersion=1)
    entry = data["projects"][PROJECT]
    del entry["parts"]
    if not request.param:
        del entry["diagnostics"]
        del entry["missingDiagnostics"]
    png = (repo / "react-app/e2e/unit.spec.ts-snapshots/unit.png").read_bytes()
    capture = entry["captures"][0]
    capture.pop("archive")
    capture.update(bytes=len(png), sha256=a.digest(png))
    original = json.dumps(data).encode()

    def zipped(rows):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            for name, body in rows:
                z.writestr(name, body)
        return stream.getvalue()

    inner = zipped([("inventory.json", original), (capture["path"], png)])
    outer = zipped([("metadata.zip", inner)])
    sha = a.digest(outer)
    base = dict(artifactId=33, archiveSha256=sha, archiveBytes=len(outer))
    prefix = dict(member="metadata.zip", bytes=len(inner), sha256=a.digest(inner))

    def binding(key, member, body):
        return dict(
            base,
            key=key,
            chain=[prefix.copy(), dict(member=member, bytes=len(body), sha256=a.digest(body))],
        )

    registry = dict(
        schemaVersion=4,
        kind="external-transport-inventory-v1",
        acceptance=False,
        runComplete=False,
        nativePartClosure="unavailable",
        provenance=identity,
        inventory=binding("inventory.json", "inventory.json", original),
        members=[binding(PROJECT + "/" + capture["path"], capture["path"], png)],
    )
    root = tmp_path / "external-supplied"
    path = root / f"external/transport/{sha}.zip"
    path.parent.mkdir(parents=True)
    path.write_bytes(outer)
    return repo, root, registry, {sha: outer}, original


def test_external_v1_retains_original_and_missing_reports_without_native_proof(external_bundle):
    from scripts.python import native_archive_evidence as native

    repo, root, registry, archives, original = external_bundle
    result = native.validate_external_inventory_transport(repo, registry, archives)
    assert result["original"] == original
    assert result["data"]["missingReports"] == json.loads(original)["missingReports"]
    assert result["externalMemberClosure"] is True
    assert result["nativePartClosure"] == "unavailable"
    assert result["acceptance"] is False and result["runComplete"] is False
    assert "parts" not in next(iter(result["data"]["projects"].values()))
    with pytest.raises(ValueError, match="no part hash closure"):
        native.validate_inventory_objects(original, registry["provenance"], {})
    catalog = archive_support.CATALOG_PATH.read_bytes()
    head = git(repo, "rev-parse", "HEAD")
    raw = json.dumps(registry).encode()
    name = typed.register_external_inventory(repo, raw, root)
    archive_support.validate_support(repo)
    files = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in (repo / "evidence/visual/support").rglob("*")
        if p.is_file()
    }
    assert typed.register_external_inventory(repo, raw, root) == name
    assert all((p.read_bytes(), p.stat().st_mtime_ns) == value for p, value in files.items())
    assert archive_support.CATALOG_PATH.read_bytes() == catalog
    assert git(repo, "rev-parse", "HEAD") == head
    retained = json.loads((repo / "evidence/visual/support" / name).read_bytes())
    assert retained["schemaVersion"] == 5
    typed.validate_external_registry(repo, retained)
    assert not (repo / "evidence/visual/support/external/transport").exists()
    with pytest.raises(ValueError):
        typed.validate_registry(repo, registry, root)


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "extra",
        "duplicate",
        "outer-hash",
        "inner-hash",
        "leaf-hash",
        "leaf-size",
        "member",
        "key",
        "source",
        "acceptance",
        "complete",
        "native-claim",
    ],
)
def test_external_v1_rejects_crossbindings(external_bundle, fault):
    from scripts.python import native_archive_evidence as native

    repo, root, registry, archives, _ = external_bundle
    row = registry["members"][0]
    if fault == "missing":
        registry["members"] = []
    elif fault == "extra":
        registry["members"].append(copy.deepcopy(row))
    elif fault == "duplicate":
        registry["inventory"]["chain"] = row["chain"]
    elif fault == "outer-hash":
        row["archiveSha256"] = "f" * 64
    elif fault == "inner-hash":
        row["chain"][0]["sha256"] = "f" * 64
    elif fault == "leaf-hash":
        row["chain"][-1]["sha256"] = "f" * 64
    elif fault == "leaf-size":
        row["chain"][-1]["bytes"] += 1
    elif fault == "member":
        row["chain"][-1]["member"] = "elsewhere.png"
    elif fault == "key":
        row["key"] = "wrong-project/file.png"
    elif fault == "source":
        registry["provenance"]["sourceTree"] = "f" * 40
    elif fault == "acceptance":
        registry["acceptance"] = True
    elif fault == "complete":
        registry["runComplete"] = True
    else:
        registry["nativePartClosure"] = "complete"
    with pytest.raises(ValueError):
        native.validate_external_inventory_transport(repo, registry, archives)


@pytest.mark.parametrize(
    "fault", ["duplicate-member", "missing-member", "unsafe-member", "wrong-png"]
)
def test_external_transport_rejects_ambiguous_or_changed_archive_members(external_bundle, fault):
    import io
    import warnings
    import zipfile

    from scripts.python import native_archive_evidence as native

    repo, _, registry, archives, _ = external_bundle
    outer = next(iter(archives.values()))
    with zipfile.ZipFile(io.BytesIO(outer)) as z:
        inner = z.read("metadata.zip")
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w") as z:
            if fault != "missing-member":
                z.writestr("metadata.zip", inner)
            if fault == "duplicate-member":
                z.writestr("metadata.zip", inner)
            if fault == "unsafe-member":
                z.writestr("../outside", b"x")
            if fault == "wrong-png":
                # Fully rehash the outer ZIP; inner identity must still fail.
                z.writestr("other.zip", inner)
    body = output.getvalue()
    sha = a.digest(body)
    for row in [registry["inventory"], *registry["members"]]:
        row.update(archiveSha256=sha, archiveBytes=len(body))
    if fault == "wrong-png":
        registry["members"][0]["chain"][-1]["sha256"] = "a" * 64
    with pytest.raises(ValueError):
        native.validate_external_inventory_transport(repo, registry, {sha: body})


@pytest.mark.parametrize("level", ["outer", "inner", "nested-extra"])
def test_external_retention_rejects_undeclared_payload_before_any_write(external_bundle, level):
    import io
    import zipfile

    repo, root, registry, archives, _ = external_bundle
    with zipfile.ZipFile(io.BytesIO(next(iter(archives.values())))) as z:
        inner = z.read("metadata.zip")

    def zipped(rows):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            for name, body in rows:
                z.writestr(name, body)
        return out.getvalue()

    if level != "outer":
        with zipfile.ZipFile(io.BytesIO(inner)) as z:
            rows = [(i.filename, z.read(i)) for i in z.infolist()]
        rows.append(
            ("unapproved-private.json", b'{"unapproved":true}')
            if level == "inner"
            else ("unapproved.zip", zipped([("trace.json", b"{}")]))
        )
        inner = zipped(rows)
    rows = [("metadata.zip", inner)]
    if level == "outer":
        rows.append(("unapproved-private.json", b'{"unapproved":true}'))
    outer = zipped(rows)
    sha = a.digest(outer)
    for row in [registry["inventory"], *registry["members"]]:
        row.update(archiveSha256=sha, archiveBytes=len(outer))
        row["chain"][0].update(sha256=a.digest(inner), bytes=len(inner))
    path = root / f"external/transport/{sha}.zip"
    path.write_bytes(outer)
    with pytest.raises(ValueError, match="unapproved archive member"):
        typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
    assert not (repo / "evidence/visual/support").exists()


@pytest.mark.parametrize(
    "payload", ["archive-comment", "member-comment", "extra-field", "prefix", "trailing"]
)
def test_external_leaf_retention_never_copies_container_payload(external_bundle, payload):
    import io
    import zipfile

    repo, root, registry, archives, _ = external_bundle
    sentinel = b"PRIVATE-CONTAINER-PAYLOAD"
    with zipfile.ZipFile(io.BytesIO(next(iter(archives.values())))) as z:
        inner = z.read("metadata.zip")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        info = zipfile.ZipInfo("metadata.zip")
        if payload == "member-comment":
            info.comment = sentinel
        if payload == "extra-field":
            info.extra = b"\xca\xfe" + len(sentinel).to_bytes(2, "little") + sentinel
        if payload == "archive-comment":
            z.comment = sentinel
        z.writestr(info, inner)
    body = out.getvalue()
    if payload == "prefix":
        body = sentinel + body
    if payload == "trailing":
        body += sentinel
    sha = a.digest(body)
    for row in [registry["inventory"], *registry["members"]]:
        row.update(archiveSha256=sha, archiveBytes=len(body))
    (root / f"external/transport/{sha}.zip").write_bytes(body)
    name = typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
    stored = repo / "evidence/visual/support"
    files = [p for p in stored.rglob("*") if p.is_file()]
    assert not any(p.suffix == ".zip" for p in files)
    assert all(sentinel not in p.read_bytes() for p in files)
    retained = json.loads((stored / name).read_bytes())
    assert retained["inventory"]["archiveSha256"] == sha
    assert retained["nativePartClosure"] == "unavailable"
    assert retained["acceptance"] is False and retained["runComplete"] is False
    archive_support.validate_support(repo)


@pytest.mark.parametrize("fault", ["private-fields", "wrong-source", "valid"])
def test_external_report_leaf_requires_closed_native_schema_before_write(external_bundle, fault):
    import io
    import zipfile

    from scripts.tests.test_native_archive_evidence import before

    repo, root, registry, archives, original = external_bundle
    data = json.loads(original)
    report = before()
    report.update({k: str(v) for k, v in registry["provenance"].items() if k != "requestedHead"})
    if fault == "private-fields":
        report["unapproved-private"] = "must not retain"
    if fault == "wrong-source":
        report["sourceCommit"] = "f" * 40
    raw = json.dumps(report).encode()
    data["originalReports"].append(
        dict(path="source-before.json", bytes=len(raw), sha256=a.digest(raw))
    )
    data["missingReports"].remove("source-before.json")
    original = json.dumps(data).encode()
    with (
        zipfile.ZipFile(io.BytesIO(next(iter(archives.values())))) as z,
        zipfile.ZipFile(io.BytesIO(z.read("metadata.zip"))) as inner,
    ):
        rows = [
            (i.filename, inner.read(i)) for i in inner.infolist() if i.filename != "inventory.json"
        ]

    def zipped(rows):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            for name, body in rows:
                z.writestr(name, body)
        return out.getvalue()

    inner = zipped(rows + [("inventory.json", original), ("source-before.json", raw)])
    body = zipped([("metadata.zip", inner)])
    sha = a.digest(body)
    extra = copy.deepcopy(registry["inventory"])
    extra["key"] = "reports/source-before.json"
    extra["chain"][-1] = dict(member="source-before.json", bytes=len(raw), sha256=a.digest(raw))
    registry["members"].append(extra)
    registry["inventory"]["chain"][-1].update(bytes=len(original), sha256=a.digest(original))
    for row in [registry["inventory"], *registry["members"]]:
        row.update(archiveSha256=sha, archiveBytes=len(body))
        row["chain"][0].update(bytes=len(inner), sha256=a.digest(inner))
    (root / f"external/transport/{sha}.zip").write_bytes(body)
    if fault == "valid":
        typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
        archive_support.validate_support(repo)
    else:
        with pytest.raises(ValueError):
            typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
        assert not (repo / "evidence/visual/support").exists()


@pytest.mark.parametrize("length", [511, 512, 513])
@pytest.mark.parametrize("level", ["outer", "leaf"])
def test_external_member_path_boundary_is_shared_before_retention(external_bundle, length, level):
    import io
    import zipfile

    from scripts.python import native_archive_evidence as native

    repo, root, registry, archives, _ = external_bundle
    def zipped(rows):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for name, body in rows:
                archive.writestr(name, body)
        return output.getvalue()

    with zipfile.ZipFile(io.BytesIO(next(iter(archives.values())))) as outer:
        inner = outer.read("metadata.zip")
    with zipfile.ZipFile(io.BytesIO(inner)) as archive:
        rows = [(info.filename, archive.read(info)) for info in archive.infolist()]
    suffix = "/inventory.json" if level == "leaf" else "/metadata.zip"
    member = "x" * (length - len(suffix)) + suffix
    if level == "leaf":
        rows = [(member if name == "inventory.json" else name, body) for name, body in rows]
        registry["inventory"]["chain"][-1]["member"] = member
    inner = zipped(rows)
    outer_name = member if level == "outer" else "metadata.zip"
    body = zipped([(outer_name, inner)])
    sha = a.digest(body)
    for row in [registry["inventory"], *registry["members"]]:
        row.update(archiveSha256=sha, archiveBytes=len(body))
        row["chain"][0].update(member=outer_name, bytes=len(inner), sha256=a.digest(inner))
    (root / f"external/transport/{sha}.zip").write_bytes(body)
    if length <= 512:
        native.validate_external_inventory_transport(repo, registry, {sha: body})
        name = typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
        retained = json.loads((repo / "evidence/visual/support" / name).read_bytes())
        typed.validate_external_registry(repo, retained)
    else:
        with pytest.raises(ValueError, match="external provenance member"):
            native.validate_external_inventory_transport(repo, registry, {sha: body})
        with pytest.raises(ValueError, match="external provenance member"):
            typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
        assert not (repo / "evidence/visual/support").exists()


def test_external_registration_prevalidates_complete_retained_profile(external_bundle, monkeypatch):
    repo, root, registry, _, _ = external_bundle
    # Model a future profile constraint that transport validation alone cannot
    # establish. It must fail before even a leaf or destination directory exists.
    def reject(*args, **kwargs):
        raise ValueError("planned retained profile rejected")
    monkeypatch.setattr(typed, "_validate_external_registry", reject, raising=False)
    with pytest.raises(ValueError, match="planned retained profile rejected"):
        typed.register_external_inventory(repo, json.dumps(registry).encode(), root)
    assert not (repo / "evidence/visual/support").exists()
