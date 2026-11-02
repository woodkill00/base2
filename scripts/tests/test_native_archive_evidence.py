"""Synthetic native-envelope schemas, distinct from original-image closure."""

import copy
import hashlib
import json

import pytest

from scripts.python import native_archive_evidence as native

PROVENANCE = dict(sourceCommit="a" * 40, sourceTree="b" * 40, runId="123", attempt="1")
TITLE = "operations center is accessible responsive and visually stable"
PROJECT = "chromium-desktop"


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode()


def before():
    return dict(
        schemaVersion=1,
        **PROVENANCE,
        matrix="operations",
        originalReporterOutput=None,
        snapshotUpdates="none",
        expectedTests=[dict(project=PROJECT, title=TITLE, expectedStatus="passed")],
    )


def after():
    return dict(
        schemaVersion=1,
        sourceCommit=PROVENANCE["sourceCommit"],
        runId="123",
        attempt="1",
        matrix="operations",
        nativeOutcome="failure",
        stats=None,
        declaredTests=1,
        statusCounts={"unexpected": 1},
        tests=[
            dict(
                project=PROJECT,
                title=TITLE,
                status="unexpected",
                attemptStatuses=["failed"],
                receiptCaptures=[],
            )
        ],
        currentCaptures=[],
        freshOperationsReceipt=False,
        sourceGuardErrors=["operations_reporter_not_produced_or_invalid"],
        unexpectedChangedPaths=[],
        scope="Native visual matrix evidence only; declared skips are not executions or whole-project acceptance.",
    )


def reporter(status="failed"):
    d = dict(
        schemaVersion=1,
        status=status,
        tests=[
            dict(
                project=PROJECT,
                title=TITLE,
                status="failed",
                assertionId="operations-primary",
                captures=[],
            )
        ],
    )
    d["digest"] = hashlib.sha256(encode(d)).hexdigest()
    return d


@pytest.mark.parametrize(
    "name,factory",
    [
        ("source-before.json", before),
        ("source-after.json", after),
        ("operations-visual-runner.json", reporter),
    ],
)
def test_closed_original_envelopes_preserve_failed_metadata(name, factory):
    value = factory()
    assert native.validate(encode(value), name, PROVENANCE) == value


@pytest.mark.parametrize("status", ["failed", "passed", "timedout", "interrupted"])
def test_reporter_preserves_original_overall_status(status):
    d = reporter(status)
    assert (
        native.validate(encode(d), "operations-visual-runner.json", PROVENANCE)["status"] == status
    )


@pytest.mark.parametrize(
    "fault",
    [
        "private-field",
        "wrong-run",
        "wrong-source",
        "unknown-producer",
        "status-count",
        "private-path",
        "unknown-error",
        "duplicate-test",
        "nonfinite",
    ],
)
def test_rejects_unbound_shapes_without_inferring_success(fault):
    d = after()
    if fault == "private-field":
        d["private"] = "not allowed"
    elif fault == "wrong-run":
        d["runId"] = "456"
    elif fault == "wrong-source":
        d["sourceCommit"] = "c" * 40
    elif fault == "unknown-producer":
        d["tests"][0]["title"] = "unrelated operation"
    elif fault == "status-count":
        d["statusCounts"]["unexpected"] = 2
    elif fault == "private-path":
        d["unexpectedChangedPaths"] = ["private/path"]
    elif fault == "unknown-error":
        d["sourceGuardErrors"] = ["private text"]
    elif fault == "duplicate-test":
        d["tests"].append(copy.deepcopy(d["tests"][0]))
    else:
        d["stats"] = dict(expected=0, unexpected=1, skipped=0, flaky=0, duration=float("nan"))
    with pytest.raises(ValueError):
        native.validate(encode(d), "source-after.json", PROVENANCE)


def test_missing_report_status_stays_unknown_not_passed():
    d = after()
    d["tests"][0].update(status=None, attemptStatuses=[None])
    d["statusCounts"] = {"null": 1}
    result = native.validate(encode(d), "source-after.json", PROVENANCE)
    assert result["tests"][0]["status"] is None and result["tests"][0]["attemptStatuses"] == [None]
    assert result["nativeOutcome"] == "failure"


def test_duplicate_json_keys_and_reporter_hash_tampering_rejected():
    raw = encode(before()).replace(b'"schemaVersion":1', b'"schemaVersion":1,"schemaVersion":1')
    with pytest.raises(ValueError, match="duplicate"):
        native.validate(raw, "source-before.json", PROVENANCE)
    d = reporter()
    d["status"] = "passed"
    with pytest.raises(ValueError, match="digest"):
        native.validate(encode(d), "operations-visual-runner.json", PROVENANCE)


@pytest.mark.parametrize("raw", [b"null", b"[]", b"1"])
def test_nonobject_roots_rejected(raw):
    with pytest.raises(ValueError):
        native.validate(raw, "source-before.json", PROVENANCE)


def test_original_reports_crossbind_freshness_results_and_declared_cases():
    b, aft, r = before(), after(), reporter()
    aft["freshOperationsReceipt"] = True
    checked = native.validate_matrix_reports(encode(b), encode(aft), encode(r), PROVENANCE)
    assert checked[1]["nativeOutcome"] == "failure"
    with pytest.raises(ValueError, match="missing declared fresh"):
        native.validate_matrix_reports(encode(b), encode(aft), None, PROVENANCE)
    aft["tests"][0]["attemptStatuses"] = ["passed"]
    with pytest.raises(ValueError, match="result mismatch"):
        native.validate_matrix_reports(encode(b), encode(aft), encode(r), PROVENANCE)


def test_failed_partial_native_report_preserves_absence():
    b, aft = before(), after()
    aft.update(tests=[], declaredTests=0, statusCounts={})
    result = native.validate_matrix_reports(encode(b), encode(aft), None, PROVENANCE)
    assert (
        result[1]["tests"] == [] and result[1]["nativeOutcome"] == "failure" and result[2] is None
    )


def inventory():
    case = native.directory(TITLE, PROJECT)
    image = f"{case}/current-operations-center.png"
    part = f"{PROJECT}.zip"
    return dict(
        schemaVersion=2,
        **PROVENANCE,
        matrix="operations",
        scope="Diagnostic packaging only; empty/missing captures are incomplete, not acceptance.",
        originalReports=[],
        missingReports=[
            "source-before.json",
            "source-after.json",
            "operations-visual-runner.json",
            "stages.md",
        ],
        projects={
            PROJECT: dict(
                status="packaged",
                captureCoverage="requires-review",
                expectedSupportedTests=before()["expectedTests"],
                currentCaptureCount=1,
                minimumCaptureShortfall=0,
                missingDiagnostics=[],
                diagnostics=[],
                captures=[dict(path=image, bytes=12, sha256="c" * 64, archive=part)],
                parts=[dict(path=part, bytes=100, sha256="d" * 64, members=[image])],
            )
        },
        errors=[],
    )


def test_historical_inventory_shape_does_not_claim_image_closure():
    value = inventory()
    assert native.validate(encode(value), "inventory.json", PROVENANCE) == value


@pytest.mark.parametrize(
    "fault",
    [
        "missing-part",
        "duplicate-member",
        "unknown-producer",
        "wrong-count",
        "new-variant",
        "duplicate-report",
        "escape",
    ],
)
def test_historical_inventory_rejects_unbound_members(fault):
    value = inventory()
    entry = value["projects"][PROJECT]
    if fault == "missing-part":
        entry["parts"] = []
    elif fault == "duplicate-member":
        entry["parts"][0]["members"] *= 2
    elif fault == "unknown-producer":
        path = f"unknown-{PROJECT}/current-operations-center.png"
        entry["captures"][0]["path"] = path
        entry["parts"][0]["members"] = [path]
    elif fault == "wrong-count":
        entry["currentCaptureCount"] = 0
    elif fault == "new-variant":
        value["complete"] = "true"
    elif fault == "duplicate-report":
        value["missingReports"].append("stages.md")
    else:
        entry["captures"][0]["path"] = "../outside.png"
    with pytest.raises(ValueError):
        native.validate(encode(value), "inventory.json", PROVENANCE)


def shell_provenance():
    suites = ["layout", "volcano", "settings", "workspace"]
    return dict(
        schemaVersion=2,
        **PROVENANCE,
        requestedHead="e" * 40,
        outcomes={s: "cancelled" for s in suites},
        shard=0,
        shards=1,
        suites={
            s: dict(sourcePresent=False, captures=0, excludedPngCount=0, nativeOutcome="cancelled")
            for s in suites
        },
        captureCount=0,
        diagnosticReceiptCount=0,
        captures=[],
        diagnostics=[],
        scope="Synthetic diagnostic PNG copies; not approved references or visual acceptance. PNG bytes hashed, not decoded by packager.",
    )


def test_original_shell_provenance_preserves_cancelled_outcome():
    data = shell_provenance()
    assert native.validate(encode(data), "provenance.json", data) == data


@pytest.mark.parametrize(
    "fault", ["new-variant", "outcome-mismatch", "unknown-suite", "shard", "total"]
)
def test_original_shell_provenance_rejects_contradictions(fault):
    data = shell_provenance()
    if fault == "new-variant":
        data["packagingComplete"] = True
    elif fault == "outcome-mismatch":
        data["suites"]["workspace"]["nativeOutcome"] = "success"
    elif fault == "unknown-suite":
        data["outcomes"]["unknown"] = "success"
    elif fault == "shard":
        data["shard"] = 1
    else:
        data["captureCount"] = 1
    with pytest.raises(ValueError):
        native.validate(encode(data), "provenance.json", data)


def inventory_objects():
    import io
    import zipfile

    data = inventory()
    entry = data["projects"][PROJECT]
    member = entry["captures"][0]
    payload = b"exact synthetic member bytes"
    member.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member["path"], payload)
    body = buffer.getvalue()
    part = entry["parts"][0]
    part.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    return data, {part["path"]: body}


def test_inventory_dependency_closure_requires_exact_original_bytes():
    data, objects = inventory_objects()
    assert native.validate_inventory_objects(encode(data), PROVENANCE, objects) == {
        data["projects"][PROJECT]["captures"][0]["path"]
    }


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "part-hash", "member-hash", "duplicate", "symlink"]
)
def test_inventory_dependency_closure_rejects_invalid_parts(fault):
    import io
    import zipfile

    data, objects = inventory_objects()
    entry = data["projects"][PROJECT]
    part = entry["parts"][0]
    if fault == "missing":
        objects.clear()
    elif fault == "extra":
        objects["extra.zip"] = b"unknown"
    elif fault == "part-hash":
        objects[part["path"]] += b"changed"
    elif fault == "member-hash":
        entry["captures"][0]["sha256"] = "f" * 64
    else:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo(entry["captures"][0]["path"])
            if fault == "symlink":
                info.external_attr = 0o120777 << 16
            archive.writestr(info, b"exact synthetic member bytes")
            if fault == "duplicate":
                with pytest.warns(UserWarning):
                    archive.writestr(info, b"exact synthetic member bytes")
        objects[part["path"]] = buffer.getvalue()
        part.update(
            bytes=len(buffer.getvalue()), sha256=hashlib.sha256(buffer.getvalue()).hexdigest()
        )
    with pytest.raises(ValueError):
        native.validate_inventory_objects(encode(data), PROVENANCE, objects)


def current_shell_provenance():
    data = shell_provenance()
    data.update(packagingComplete=True, packagingErrors=[])
    data["scope"] = (
        "Synthetic diagnostic PNG copies; not approved references or visual acceptance. "
        "PNG bytes hashed; confirmation schema 2 images additionally decoded and endpoint-bound. "
        "Historical ownership schema 1 is not endpoint proof."
    )
    data["outcomes"]["journeys"] = "cancelled"
    data["suites"]["journeys"] = copy.deepcopy(data["suites"]["workspace"])
    for row in data["suites"].values():
        row.update(producerExclusions=[], unknownExcludedCount=0)
    return data


def test_current_envelope_retains_exclusions_without_claiming_duplicate_bytes():
    data = current_shell_provenance()
    row = data["suites"]["layout"]
    row.update(
        excludedPngCount=2,
        unknownExcludedCount=1,
        producerExclusions=[
            dict(
                path="fixture-chromium/attachments/Rendered-page-" + "a" * 40 + ".png",
                classification="known-attachment-copy-excluded",
            )
        ],
    )
    checked = native.validate(encode(data), "provenance.json", data)
    assert checked == data
    assert checked["outcomes"]["layout"] == "cancelled"
    assert "byteEquality" not in checked["suites"]["layout"]


@pytest.mark.parametrize(
    "fault",
    ["count", "duplicate", "escape", "extra", "wrong-class", "wrong-scope", "mixed-history"],
)
def test_current_envelope_rejects_exclusion_contradictions(fault):
    data = current_shell_provenance()
    row = data["suites"]["workspace"]
    entry = dict(
        path="fixture-chromium/attachments/Rendered-page-" + "a" * 40 + ".png",
        classification="known-attachment-copy-excluded",
    )
    row.update(excludedPngCount=1, producerExclusions=[entry])
    if fault == "count":
        row["unknownExcludedCount"] = 1
    elif fault == "duplicate":
        row.update(excludedPngCount=2, producerExclusions=[entry, entry])
    elif fault == "escape":
        entry["path"] = "../attachments/Rendered-page-" + "a" * 40 + ".png"
    elif fault == "extra":
        entry["byteEquality"] = True
    elif fault == "wrong-class":
        entry["classification"] = "identical"
    elif fault == "wrong-scope":
        data["scope"] = "Unknown verification scope"
    else:
        del row["unknownExcludedCount"]
    with pytest.raises(ValueError):
        native.validate(encode(data), "provenance.json", data)


def test_current_inventory_complete_is_packaging_only_and_rejects_shortfall():
    data = inventory()
    data["originalReports"] = [
        dict(path=n, bytes=1, sha256="c" * 64) for n in data["missingReports"]
    ]
    data["missingReports"] = []
    data["complete"] = True
    assert native.validate(encode(data), "inventory.json", PROVENANCE) == data
    data["projects"][PROJECT]["minimumCaptureShortfall"] = 1
    with pytest.raises(ValueError, match="complete contradiction"):
        native.validate(encode(data), "inventory.json", PROVENANCE)
    data["complete"] = False
    assert native.validate(encode(data), "inventory.json", PROVENANCE)["complete"] is False


def provenance_objects():
    # A failed run may still have an intact retained object set.
    data = current_shell_provenance()
    raw = encode({"schemaVersion": 1})
    path = "workspace/fixture-chromium/workspace-capture-ownership.json"
    data["diagnostics"] = [
        dict(
            path=path,
            bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            sourceRoot="workspace",
            role="workspace-ownership-diagnostic",
        )
    ]
    data["diagnosticReceiptCount"] = 1
    return data, {path: raw}


def test_provenance_crosspart_identity_is_not_semantic_acceptance():
    data, objects = provenance_objects()
    assert native.validate_provenance_objects([encode(data)], data, objects) == {}
    assert data["outcomes"]["workspace"] == "cancelled"


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "extra",
        "changed",
        "missing-shard",
        "duplicate-shard",
        "global-count",
        "duplicate-json",
    ],
)
def test_provenance_crosspart_dependencies_are_mandatory(fault):
    data, objects = provenance_objects()
    if fault == "missing":
        objects.clear()
    elif fault == "extra":
        objects["unregistered.json"] = b"{}"
    elif fault == "changed":
        objects[next(iter(objects))] += b" "
    elif fault == "missing-shard":
        data["shards"] = 2
    elif fault == "global-count":
        data["diagnosticReceiptCount"] = 2
    elif fault == "duplicate-json":
        raw = b'{"schemaVersion":1,"schemaVersion":1}'
        objects[next(iter(objects))] = raw
        data["diagnostics"][0].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    shards = [encode(data)]
    if fault == "duplicate-shard":
        data["shards"] = 2
        shards = [encode(data), encode(data)]
    with pytest.raises(ValueError):
        native.validate_provenance_objects(shards, data, objects)


def test_seven_suite_provenance_media_role_is_exact_and_fail_closed():
    data = current_shell_provenance()
    for suite in ["media_hc", "operations_hc"]:
        data["outcomes"][suite] = "cancelled"
        data["suites"][suite] = copy.deepcopy(data["suites"]["workspace"])
    data["diagnostics"] = [
        dict(
            path="media_hc/media-release-media-librar-1b4ce-nsive-and-visually-reviewed-chromium-high-contrast/media-viewport-observations.json",
            bytes=10,
            sha256="a" * 64,
            sourceRoot="media_hc",
            role="media-viewport-diagnostic",
        )
    ]
    data["diagnosticReceiptCount"] = 1
    assert native.validate(encode(data), "provenance.json", data) == data
    bad = copy.deepcopy(data)
    bad["diagnostics"][0]["path"] = bad["diagnostics"][0]["path"].replace(
        "chromium-high-contrast", "chromium-desktop"
    )
    with pytest.raises(ValueError):
        native.validate(encode(bad), "provenance.json", bad)
    bad = copy.deepcopy(data)
    bad["packagingErrors"] = ["unknown"]
    with pytest.raises(ValueError):
        native.validate(encode(bad), "provenance.json", bad)


def legacy_hc():
    case = "workspace-release-workspac-d0657-ponsive-and-visually-stable-chromium-high-contrast"
    return dict(
        schemaVersion=1,
        **PROVENANCE,
        requestedHead="e" * 40,
        workspaceOutcome="failure",
        view="schema",
        captures=[dict(path=case + "/workspace-schema-post-assert.png", bytes=12, sha256="c" * 64)],
        scope="Diagnostic HC PNG copies only; no visual acceptance.",
    )


def test_historical_counted_packaging_keeps_hash_only_scope():
    data = current_shell_provenance()
    data["scope"] = native.HASH_ONLY_SCOPE
    raw = encode(data)
    classified = native.classify_original(raw, "provenance.json", data)
    assert classified["profile"] == "shell-hash-only-v2"
    assert classified["original"] == raw and classified["data"] == data
    assert classified["acceptance"] is False and classified["closure"] is False
    assert data["outcomes"]["workspace"] == "cancelled"


@pytest.mark.parametrize("with_diagnostics", [False, True])
def test_exact_legacy_inventory_profiles_do_not_invent_parts(with_diagnostics):
    data = inventory()
    data["schemaVersion"] = 1
    row = data["projects"][PROJECT]
    del row["parts"]
    for capture in row["captures"]:
        del capture["archive"]
    if not with_diagnostics:
        del row["diagnostics"]
        del row["missingDiagnostics"]
    raw = encode(data)
    checked = native.classify_original(raw, "inventory.json", PROVENANCE)
    assert checked["data"] == data and checked["profile"] == "matrix-v1"
    assert checked["closure"] is False
    with pytest.raises(ValueError, match="no part hash closure"):
        native.validate_inventory_objects(raw, PROVENANCE, {})
    data["projects"][PROJECT]["parts"] = []
    with pytest.raises(ValueError):
        native.validate(encode(data), "inventory.json", PROVENANCE)


def test_legacy_hc_preserves_failure_and_rejects_other_view_or_source():
    data = legacy_hc()
    raw = encode(data)
    checked = native.classify_original(raw, "provenance.json", data)
    assert checked["profile"] == "hc-view-hash-only-v1"
    assert checked["data"]["workspaceOutcome"] == "failure"
    assert checked["original"] == raw and checked["closure"] is False
    for fault in ("view", "source", "duplicate", "extra"):
        bad = copy.deepcopy(data)
        if fault == "view":
            bad["view"] = "records"
        elif fault == "source":
            bad["sourceTree"] = "f" * 40
        elif fault == "duplicate":
            bad["captures"] *= 2
        else:
            bad["complete"] = True
        with pytest.raises(ValueError):
            native.validate(encode(bad), "provenance.json", data)


def test_contradictory_complete_inventory_is_quarantined_never_proof():
    data = inventory()
    data["complete"] = True
    raw = encode(data)
    with pytest.raises(ValueError, match="complete reports contradiction"):
        native.validate(raw, "inventory.json", PROVENANCE)
    result = native.classify_original(raw, "inventory.json", PROVENANCE)
    assert result["status"] == "quarantined-invalid-diagnostic"
    assert result["original"] == raw and result["data"]["complete"] is True
    assert result["data"]["errors"] == [] and result["data"]["missingReports"]
    assert result["acceptance"] is False and result["closure"] is False
    with pytest.raises(ValueError):
        native.validate_inventory_objects(raw, PROVENANCE, {})
    # Every completeness contradiction remains explicit; malformed shape is rejected.
    data["projects"][PROJECT]["minimumCaptureShortfall"] = 1
    result = native.classify_original(encode(data), "inventory.json", PROVENANCE)
    assert result["contradictions"] == [
        "complete-with-missing-reports",
        "complete-with-incomplete-projects",
    ]
    data["projects"][PROJECT]["currentCaptureCount"] = 999
    with pytest.raises(ValueError):
        native.classify_original(encode(data), "inventory.json", PROVENANCE)


@pytest.mark.parametrize("view", ["records", "schema", "imports", "exports"])
def test_named_hc_profiles_reject_cross_view_pair(view):
    data = legacy_hc()
    data["view"] = view
    data["captures"][0]["path"] = (
        native.hc_case("pairs", view) + f"/workspace-{view}-post-assert.png"
    )
    assert native.validate(encode(data), "provenance.json", data) == data
    other = "imports" if view in {"records", "schema"} else "records"
    data["captures"][0]["path"] = (
        native.hc_case("pairs", other) + f"/workspace-{view}-post-assert.png"
    )
    with pytest.raises(ValueError, match="producer profile"):
        native.validate(encode(data), "provenance.json", data)
