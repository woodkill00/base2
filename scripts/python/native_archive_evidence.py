"""Closed original matrix metadata schemas. Shape validation is not image closure.

These readers preserve failed/skipped/interrupted/unknown observations. They do
not infer an outcome, execute historical producers, or grant visual acceptance.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import re

from scripts.python import continuous_evidence, sequence_evidence
from scripts.python import screenshot_archive as a
from scripts.python.archive_support import directory
from scripts.python.typed_archive_support import MATRIX_PROJECTS, fields, producer_title

BUDGET = 2 * 1024 * 1024
GUARD_ERRORS = {
    "visual_source_changed",
    "visual_inputs_or_baselines_changed",
    "successful_matrix_missing_full_inventory",
    "successful_matrix_zero_supported_execution",
    "successful_matrix_supported_or_skip_status_mismatch",
    "unsafe_current_capture",
    "successful_matrix_missing_current_captures",
    "native_reporter_digest_invalid",
    "successful_operations_reporter_inventory_mismatch",
    "operations_reporter_attachment_mismatch",
    "operations_reporter_not_produced_or_invalid",
    "successful_operations_missing_fresh_reporter",
}
ATTEMPT_STATUSES = {"passed", "failed", "timedOut", "skipped", "interrupted"}
REPORT_STATUSES = {"expected", "unexpected", "flaky", "skipped"}


def number(value, integer=True):
    a.require(type(value) is int if integer else type(value) in (int, float), "native number type")
    a.require(math.isfinite(value) and 0 <= value <= 10**20, "native number range")


def digest(value):
    a.require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "native digest")


def identity(data, provenance, tree=True):
    for key in ("sourceCommit", "runId", "attempt") + (("sourceTree",) if tree else ()):
        a.require(
            type(data[key]) is str and data[key] == str(provenance[key]),
            "native source/run mismatch",
        )
    a.require(re.fullmatch("[0-9a-f]{40}", data["sourceCommit"]), "native source")
    if tree:
        a.require(re.fullmatch("[0-9a-f]{40}", data["sourceTree"]), "native tree")
    for key in ("runId", "attempt"):
        a.require(re.fullmatch("[0-9]{1,20}", data[key]), "native run identity")


def test_identity(row, matrix):
    a.require(
        type(row["project"]) is str and re.fullmatch(MATRIX_PROJECTS, row["project"]),
        "native project",
    )
    a.require(type(row["title"]) is str and len(row["title"]) <= 160, "native title")
    case = directory(row["title"], row["project"])
    a.require(producer_title(matrix, case, row["project"]) == row["title"], "native exact producer")
    return row["project"], row["title"]


def captures(rows):
    a.require(type(rows) is list and len(rows) <= 512, "native attachment bound")
    names = set()
    for row in rows:
        fields(row, "name sha256")
        a.require(
            type(row["name"]) is str
            and re.fullmatch(
                r"(?:media-(?:detail|library|picker)|operations-center)[a-z0-9-]{0,180}\.png",
                row["name"],
            )
            and row["name"] not in names,
            "native attachment name",
        )
        names.add(row["name"])
        digest(row["sha256"])


def expected_tests(rows, matrix):
    a.require(type(rows) is list and 0 < len(rows) <= 128, "native expected count")
    seen = set()
    for row in rows:
        fields(row, "project title expectedStatus")
        key = test_identity(row, matrix)
        a.require(
            key not in seen and row["expectedStatus"] in {"passed", "skipped"},
            "native expected state",
        )
        seen.add(key)


def _validate(raw, name, provenance):
    a.require(0 < len(raw) <= BUDGET, "native metadata bound")
    data = sequence_evidence.strict_json(raw)
    if name in {"inventory.json", "provenance.json"}:
        a.require(
            type(data) is dict
            and type(data.get("schemaVersion")) is int
            and data["schemaVersion"] in {1, 2},
            "native metadata version",
        )
        return (
            old_inventory(data, provenance)
            if name == "inventory.json"
            else (
                hc_provenance_v1(data, provenance)
                if data["schemaVersion"] == 1
                else old_provenance(data, provenance)
            )
        )
    a.require(
        type(data) is dict
        and type(data.get("schemaVersion")) is int
        and data["schemaVersion"] == 1,
        "native metadata version",
    )
    if name == "operations-visual-runner.json":
        fields(data, "schemaVersion status tests digest")
        a.require(
            data["status"] in {"passed", "failed", "timedout", "interrupted"},
            "native reporter status",
        )
        digest(data["digest"])
        body = {k: v for k, v in data.items() if k != "digest"}
        a.require(
            hashlib.sha256(
                json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest()
            == data["digest"],
            "native reporter digest",
        )
        a.require(
            type(data["tests"]) is list and len(data["tests"]) <= 128, "native reporter count"
        )
        seen = set()
        for row in data["tests"]:
            fields(row, "project title status assertionId captures")
            key = test_identity(row, "operations")
            a.require(
                key not in seen and row["status"] in ATTEMPT_STATUSES, "native reporter test status"
            )
            seen.add(key)
            wanted = (
                "operations-primary"
                if row["title"] == "operations center is accessible responsive and visually stable"
                else "operations-recovery"
                if "stale, reauthentication" in row["title"]
                else "operations-empty-error"
            )
            a.require(row["assertionId"] == wanted, "native reporter assertion")
            captures(row["captures"])
        return data
    a.require(name in {"source-before.json", "source-after.json"}, "unsupported native member")
    a.require(data.get("matrix") in {"media", "operations"}, "native matrix")
    if name == "source-before.json":
        fields(
            data,
            "schemaVersion sourceCommit sourceTree matrix runId attempt originalReporterOutput snapshotUpdates expectedTests",
        )
        identity(data, provenance)
        a.require(data["snapshotUpdates"] == "none", "native snapshot update policy")
        signature = data["originalReporterOutput"]
        if signature is not None:
            fields(signature, "sha256 mtimeNs")
            digest(signature["sha256"])
            number(signature["mtimeNs"])
        expected_tests(data["expectedTests"], data["matrix"])
        return data
    fields(
        data,
        "schemaVersion sourceCommit matrix runId attempt nativeOutcome stats declaredTests statusCounts tests currentCaptures freshOperationsReceipt sourceGuardErrors unexpectedChangedPaths scope",
    )
    identity(data, provenance, tree=False)
    a.require(
        data["nativeOutcome"] in {"success", "failure", "cancelled", "skipped"}, "native outcome"
    )
    a.require(
        data["scope"]
        == "Native visual matrix evidence only; declared skips are not executions or whole-project acceptance.",
        "native scope",
    )
    a.require(type(data["freshOperationsReceipt"]) is bool, "native receipt flag")
    stats = data["stats"]
    if stats is not None:
        fields(stats, "expected unexpected skipped flaky duration")
        for key, value in stats.items():
            if value is not None:
                number(value, integer=key != "duration")
    a.require(type(data["tests"]) is list and len(data["tests"]) <= 128, "native observed count")
    seen = set()
    for row in data["tests"]:
        fields(row, "project title status attemptStatuses receiptCaptures")
        key = test_identity(row, data["matrix"])
        a.require(
            key not in seen and row["status"] in REPORT_STATUSES | {None}, "native observed test"
        )
        seen.add(key)
        a.require(
            type(row["attemptStatuses"]) is list
            and len(row["attemptStatuses"]) <= 4
            and all(v in ATTEMPT_STATUSES | {None} for v in row["attemptStatuses"]),
            "native attempt statuses",
        )
        captures(row["receiptCaptures"])
    a.require(
        type(data["declaredTests"]) is int and data["declaredTests"] == len(data["tests"]),
        "native declared count",
    )
    expected_counts = dict(
        collections.Counter(
            str(row["status"]) if row["status"] is not None else "null" for row in data["tests"]
        )
    )
    a.require(
        type(data["statusCounts"]) is dict
        and data["statusCounts"] == expected_counts
        and all(type(v) is int for v in data["statusCounts"].values()),
        "native status counts",
    )
    a.require(
        type(data["currentCaptures"]) is list and len(data["currentCaptures"]) <= 65536,
        "native capture bound",
    )
    seen = set()
    for row in data["currentCaptures"]:
        fields(row, "path sha256")
        a.require(type(row["path"]) is str and len(row["path"]) <= 300, "native capture path")
        pieces = row["path"].split("/")
        a.require(
            len(pieces) == 3
            and pieces[0] == "test-results"
            and re.fullmatch(r"current-[a-z0-9-]{1,200}\.png", pieces[2]),
            "native current member",
        )
        a.require(
            any(
                pieces[1] == directory(title, project)
                for project, title in seen_tests(data["tests"])
            ),
            "native current producer",
        )
        a.require(row["path"] not in seen, "native duplicate capture")
        seen.add(row["path"])
        digest(row["sha256"])
    a.require(
        type(data["sourceGuardErrors"]) is list
        and len(data["sourceGuardErrors"]) <= 20
        and all(v in GUARD_ERRORS for v in data["sourceGuardErrors"]),
        "native guard errors",
    )
    # No supplied original contains changed-path payloads. Fail closed until that
    # diagnostic variant has a separately reviewed privacy schema.
    a.require(data["unexpectedChangedPaths"] == [], "unsupported native changed-path diagnostic")
    return data


def seen_tests(rows):
    return {(row["project"], row["title"]) for row in rows}


def validate(raw, name, provenance):
    try:
        return _validate(raw, name, provenance)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
        raise ValueError("invalid native metadata shape") from error


def validate_matrix_reports(before_raw, after_raw, runner_raw, provenance):
    """Crossbind supplied original reports without assigning a derived outcome.

    Inventory/PNG dependency closure is a separate mandatory registration step;
    a return value here only establishes these three reports' mutual consistency.
    """
    before = validate(before_raw, "source-before.json", provenance)
    after = validate(after_raw, "source-after.json", provenance)
    a.require(before["matrix"] == after["matrix"], "native report matrix mismatch")
    expected = {(row["project"], row["title"]) for row in before["expectedTests"]}
    observed = {(row["project"], row["title"]): row for row in after["tests"]}
    a.require(set(observed) <= expected, "native observed undeclared producer")
    runner = None
    if runner_raw is not None:
        a.require(
            before["matrix"] == "operations" and after["freshOperationsReceipt"],
            "native unexpected reporter",
        )
        runner = validate(runner_raw, "operations-visual-runner.json", provenance)
        reported = {(row["project"], row["title"]): row for row in runner["tests"]}
        a.require(set(reported) == set(observed), "native reporter inventory mismatch")
        for key, row in reported.items():
            a.require(
                observed[key]["attemptStatuses"] == [row["status"]]
                and observed[key]["receiptCaptures"] == row["captures"],
                "native reporter result mismatch",
            )
    else:
        a.require(not after["freshOperationsReceipt"], "missing declared fresh reporter")
    return before, after, runner


def object_descriptor(row, extras=""):
    fields(row, "path bytes sha256 " + extras)
    a.require(
        type(row["path"]) is str
        and 0 < len(row["path"]) <= 300
        and re.fullmatch(r"[a-zA-Z0-9_.\-/]+", row["path"])
        and all(p not in {"", ".", ".."} for p in row["path"].split("/")),
        "native object path",
    )
    number(row["bytes"])
    a.require(0 < row["bytes"] <= 32 * 1024 * 1024, "native object size")
    digest(row["sha256"])


HASH_ONLY_SCOPE = "Synthetic diagnostic PNG copies; not approved references or visual acceptance. PNG bytes hashed, not decoded by packager."
ENDPOINT_SCOPE = "Synthetic diagnostic PNG copies; not approved references or visual acceptance. PNG bytes hashed; confirmation schema 2 images additionally decoded and endpoint-bound. Historical ownership schema 1 is not endpoint proof."


def hc_case(profile, view):
    suffix = (
        "d0657" if profile == "aggregate" else "92e7c" if view in {"records", "schema"} else "a27fb"
    )
    return f"workspace-release-workspac-{suffix}-ponsive-and-visually-stable-chromium-high-contrast"


def hc_provenance_v1(data, provenance):
    """Original view-local HC copies, with no diagnostic or run-completeness claim."""
    fields(
        data,
        "schemaVersion sourceCommit sourceTree requestedHead runId attempt workspaceOutcome view captures scope",
    )
    identity(data, provenance)
    a.require(
        data["requestedHead"] == provenance["requestedHead"]
        and re.fullmatch("[a-f0-9]{40}", data["requestedHead"]),
        "native requested head",
    )
    a.require(
        data["scope"] == "Diagnostic HC PNG copies only; no visual acceptance.", "native HC scope"
    )
    a.require(
        data["workspaceOutcome"] in {"success", "failure", "skipped", "cancelled"},
        "native HC outcome",
    )
    a.require(data["view"] in {"records", "schema", "imports", "exports"}, "native HC view")
    a.require(
        type(data["captures"]) is list and len(data["captures"]) <= 2048, "native HC captures"
    )
    cases = {hc_case("aggregate", data["view"]), hc_case("pairs", data["view"])}
    seen = set()
    producers = set()
    for row in data["captures"]:
        object_descriptor(row)
        path = row["path"]
        pieces = path.split("/")
        a.require(len(pieces) == 2 and pieces[0] in cases, "native HC producer profile")
        producers.add(pieces[0])
        a.require(
            path not in seen
            and re.fullmatch(
                re.escape(pieces[0] + "/workspace-" + data["view"])
                + r"(?:-chromium-high-contrast-(?:actual|expected|diff)|-post-assert)\.png",
                path,
            ),
            "native HC producer/view",
        )
        seen.add(path)
    a.require(len(producers) <= 1, "native HC mixed producer profiles")
    return data


def inventory_contradictions(data):
    reasons = []
    if data.get("complete") is True:
        if data["missingReports"]:
            reasons.append("complete-with-missing-reports")
        if any(
            e["status"] != "packaged"
            or e["minimumCaptureShortfall"] != 0
            or e.get("missingDiagnostics", [])
            for e in data["projects"].values()
        ):
            reasons.append("complete-with-incomplete-projects")
    return reasons


def classify_original(raw, name, provenance):
    """Non-mutating retention classification. Invalid bytes never enter proof APIs.

    The sole known contradiction is admitted only for quarantine after the rest
    of its closed inventory shape validates. Original bytes and fields remain
    unchanged; this is not a registration or dependency-closure result.
    """
    try:
        data = validate(raw, name, provenance)
    except ValueError as error:
        if (
            name != "inventory.json"
            or str(error) != "native inventory complete reports contradiction"
        ):
            raise
        data = sequence_evidence.strict_json(raw)
        old_inventory(data, provenance, quarantine_contradiction=True)
        return dict(
            status="quarantined-invalid-diagnostic",
            reason="contradictory-completeness",
            contradictions=inventory_contradictions(data),
            sha256=a.digest(raw),
            bytes=len(raw),
            original=raw,
            data=data,
            acceptance=False,
            closure=False,
        )
    profile = (
        "hc-view-hash-only-v1"
        if name == "provenance.json" and data["schemaVersion"] == 1
        else "shell-hash-only-v2"
        if name == "provenance.json" and data["scope"] == HASH_ONLY_SCOPE
        else "shell-endpoint-aware-v2"
        if name == "provenance.json"
        else "matrix-v" + str(data["schemaVersion"])
    )
    return dict(
        status="validated-shape",
        profile=profile,
        sha256=a.digest(raw),
        bytes=len(raw),
        original=raw,
        data=data,
        acceptance=False,
        closure=False,
    )


def old_inventory(data, provenance, *, quarantine_contradiction=False):
    # Historical v1 has no part identities; do not manufacture those fields.
    legacy = data["schemaVersion"] == 1
    current = "complete" in data
    a.require(not legacy or not current, "native v1 completeness field")
    fields(
        data,
        "schemaVersion sourceCommit sourceTree runId attempt matrix scope originalReports missingReports projects errors"
        + (" complete" if current else ""),
    )
    identity(data, provenance)
    a.require(
        data["matrix"] in {"media", "operations"}
        and data["scope"]
        == "Diagnostic packaging only; empty/missing captures are incomplete, not acceptance.",
        "native inventory scope",
    )
    reports = {
        "source-before.json",
        "source-after.json",
        "operations-visual-runner.json",
        "stages.md",
    }
    a.require(
        type(data["originalReports"]) is list and len(data["originalReports"]) <= 4,
        "native report count",
    )
    seen = set()
    for row in data["originalReports"]:
        object_descriptor(row)
        a.require(row["path"] in reports and row["path"] not in seen, "native report name")
        seen.add(row["path"])
    a.require(
        type(data["missingReports"]) is list
        and len(data["missingReports"]) == len(set(data["missingReports"]))
        and set(data["missingReports"]) == reports - seen,
        "native missing reports",
    )
    a.require(
        type(data["projects"]) is dict and 0 < len(data["projects"]) <= 32,
        "native project inventory",
    )
    for project, entry in data["projects"].items():
        a.require(re.fullmatch(MATRIX_PROJECTS, project), "native inventory project")
        fields(
            entry,
            "status captures expectedSupportedTests currentCaptureCount minimumCaptureShortfall captureCoverage"
            + (" diagnostics missingDiagnostics" if not legacy or "diagnostics" in entry else "")
            + (" parts" if not legacy else ""),
        )
        a.require(
            entry["status"] in {"packaged", "incomplete"}
            and entry["captureCoverage"] in {"requires-review", "incomplete"},
            "native packaging status",
        )
        if entry["expectedSupportedTests"]:
            expected_tests(entry["expectedSupportedTests"], data["matrix"])
            a.require(
                all(row["project"] == project for row in entry["expectedSupportedTests"]),
                "native supported project",
            )
        else:
            a.require(entry["expectedSupportedTests"] == [], "native supported shape")
        for key in ("currentCaptureCount", "minimumCaptureShortfall"):
            number(entry[key])
        members = {}
        for category in ("captures", "diagnostics"):
            a.require(
                type(entry.get(category, [])) is list and len(entry.get(category, [])) <= 65536,
                "native member bound",
            )
            for row in entry.get(category, []):
                # Geometry records have no complete/kind fields; continuous and
                # comparison records have the exact additional pair.
                extras = (
                    "archive"
                    if category == "captures" or "kind" not in row
                    else "archive complete kind"
                )
                object_descriptor(row, "" if legacy else extras)
                pieces = row["path"].split("/")
                a.require(
                    len(pieces) == 2
                    and producer_title(data["matrix"], pieces[0], project) is not None,
                    "native member producer project",
                )
                a.require(row["path"] not in members, "native duplicate member")
                if category == "captures":
                    from scripts.python.visual_matrix_artifacts import PNG_NAME

                    a.require(PNG_NAME.fullmatch(pieces[1]), "native PNG member")
                elif "kind" in row:
                    a.require(
                        type(row["complete"]) is bool
                        and row["kind"] in {"continuous-viewports", "sequence-comparison"},
                        "native diagnostic kind",
                    )
                    pattern = (
                        sequence_evidence.NAME
                        if row["kind"] == "sequence-comparison"
                        else continuous_evidence.NAME
                    )
                    a.require(pattern.fullmatch(pieces[1]), "native diagnostic member")
                else:
                    a.require(
                        pieces[1] == "media-viewport-observations.json"
                        and data["matrix"] == "media",
                        "native geometry member",
                    )
                if legacy:
                    members[row["path"]] = None
                    continue
                a.require(
                    type(row["archive"]) is str
                    and re.fullmatch(
                        re.escape(project) + r"(?:-part-[0-9]+)?\.zip", row["archive"]
                    ),
                    "native part name",
                )
                members[row["path"]] = row["archive"]
        a.require(
            type(entry.get("parts", [])) is list and len(entry.get("parts", [])) <= 480,
            "native parts bound",
        )
        bound = set()
        parts = set()
        for row in entry.get("parts", []):
            object_descriptor(row, "members")
            a.require(
                row["path"] not in parts
                and re.fullmatch(re.escape(project) + r"(?:-part-[0-9]+)?\.zip", row["path"]),
                "native duplicate part",
            )
            parts.add(row["path"])
            a.require(
                type(row["members"]) is list and len(row["members"]) <= 65536, "native part members"
            )
            for member in row["members"]:
                a.require(
                    member not in bound and members.get(member) == row["path"],
                    "native part membership",
                )
                bound.add(member)
        a.require(legacy or bound == set(members), "native missing part member")
        a.require(
            entry["currentCaptureCount"]
            == sum(row["path"].split("/")[-1].startswith("current-") for row in entry["captures"]),
            "native current capture count",
        )
        a.require(
            entry.get("missingDiagnostics", []) in ([], ["media-viewport-observations.json"]),
            "native missing diagnostics",
        )
    a.require(data["errors"] == [], "unsupported historical packaging-error variant")
    if current:
        a.require(type(data["complete"]) is bool, "native inventory complete type")
        if data["complete"]:
            a.require(
                quarantine_contradiction or (not data["missingReports"] and not data["errors"]),
                "native inventory complete reports contradiction",
            )
            a.require(
                quarantine_contradiction
                or all(
                    e["status"] == "packaged"
                    and e["minimumCaptureShortfall"] == 0
                    and not e["missingDiagnostics"]
                    for e in data["projects"].values()
                ),
                "native inventory complete contradiction",
            )
    return data


def old_provenance(data, provenance):
    current = "packagingComplete" in data
    fields(
        data,
        "schemaVersion sourceCommit sourceTree requestedHead runId attempt outcomes shard shards suites captureCount diagnosticReceiptCount scope captures diagnostics"
        + (" packagingComplete packagingErrors" if current else ""),
    )
    identity(data, provenance)
    a.require(
        type(data["requestedHead"]) is str
        and re.fullmatch("[a-f0-9]{40}", data["requestedHead"])
        and data["requestedHead"] == str(provenance["requestedHead"]),
        "native requested head",
    )
    a.require(
        data["scope"] in ({HASH_ONLY_SCOPE, ENDPOINT_SCOPE} if current else {HASH_ONLY_SCOPE}),
        "native provenance scope",
    )
    suites = {"layout", "volcano", "settings", "workspace"}
    if current:
        suites.add("journeys")
        if set(data["suites"]) == suites | {"media_hc", "operations_hc"}:
            suites |= {"media_hc", "operations_hc"}
        a.require(type(data["packagingComplete"]) is bool, "native packaging complete type")
        a.require(data["packagingErrors"] == [], "unsupported packaging-error variant")
    a.require(
        type(data["outcomes"]) is dict
        and set(data["outcomes"]) == suites
        and all(
            v in {"success", "failure", "skipped", "cancelled"} for v in data["outcomes"].values()
        ),
        "native suite outcomes",
    )
    a.require(type(data["suites"]) is dict and set(data["suites"]) == suites, "native suites")
    for suite, row in data["suites"].items():
        fields(
            row,
            "sourcePresent captures excludedPngCount nativeOutcome"
            + (" producerExclusions unknownExcludedCount" if current else ""),
        )
        if current:
            number(row["unknownExcludedCount"])
            exclusions = row["producerExclusions"]
            a.require(
                type(exclusions) is list and len(exclusions) <= 1024, "native exclusions bound"
            )
            seen_exclusions = set()
            for excluded in exclusions:
                fields(excluded, "path classification")
                path = excluded["path"]
                a.require(
                    type(path) is str
                    and len(path) <= 300
                    and re.fullmatch(
                        r"[a-zA-Z0-9_-]+/attachments/[a-zA-Z0-9_-]+-[0-9a-f]{40}\.png", path
                    )
                    and path not in seen_exclusions,
                    "native exclusion path",
                )
                a.require(
                    excluded["classification"] == "known-attachment-copy-excluded",
                    "native exclusion class",
                )
                seen_exclusions.add(path)
            a.require(
                len(exclusions) + row["unknownExcludedCount"] == row["excludedPngCount"],
                "native exclusion count",
            )
        a.require(
            type(row["sourcePresent"]) is bool and row["nativeOutcome"] == data["outcomes"][suite],
            "native suite outcome mismatch",
        )
        number(row["captures"])
        number(row["excludedPngCount"])
    for key in ("shard", "shards", "captureCount", "diagnosticReceiptCount"):
        number(data[key])
    a.require(0 <= data["shard"] < data["shards"] <= 480, "native shard index")
    a.require(
        data["captureCount"] == sum(r["captures"] for r in data["suites"].values()),
        "native total captures",
    )
    names = set()
    for category in ("captures", "diagnostics"):
        a.require(
            type(data[category]) is list and len(data[category]) <= 2048, "native shard members"
        )
        for row in data[category]:
            object_descriptor(row, "sourceRoot role")
            pieces = row["path"].split("/")
            a.require(
                len(pieces) == 3
                and pieces[0] == row["sourceRoot"]
                and row["sourceRoot"] in suites
                and row["path"] not in names,
                "native shard source",
            )
            names.add(row["path"])
            if category == "captures":
                a.require(
                    pieces[-1].endswith(".png")
                    and row["role"]
                    in {
                        "current-diagnostic",
                        "failure-diagnostic",
                        "comparison-actual",
                        "comparison-expected",
                        "comparison-diff",
                        "original-focus-context",
                    },
                    "native capture role",
                )
            else:
                a.require(
                    pieces[-1].endswith(".json")
                    and row["role"]
                    in (
                        {"continuous-diagnostic-receipt", "sequence-comparison-receipt"}
                        | (
                            {
                                "workspace-ownership-diagnostic",
                                "workspace-phase-diagnostic",
                                "confirmation-endpoint-diagnostic",
                                "media-viewport-diagnostic",
                            }
                            if current
                            else set()
                        )
                    ),
                    "native receipt role",
                )
                if row["role"] == "media-viewport-diagnostic":
                    a.require(
                        row["sourceRoot"] == "media_hc"
                        and pieces[1]
                        == "media-release-media-librar-1b4ce-nsive-and-visually-reviewed-chromium-high-contrast"
                        and pieces[-1] == "media-viewport-observations.json",
                        "native media diagnostic producer",
                    )
                exact_names = {
                    "workspace-ownership-diagnostic": r"workspace-capture-ownership\.json",
                    "workspace-phase-diagnostic": r"workspace-scroll-checkpoints\.json",
                    "confirmation-endpoint-diagnostic": r"workspace-confirm-(?:submit-review|publish|delete|restore)-capture\.json",
                }
                if row["role"] in exact_names:
                    a.require(
                        row["sourceRoot"] == "workspace"
                        and re.fullmatch(exact_names[row["role"]], pieces[-1]),
                        "native workspace diagnostic name",
                    )
    a.require(
        len(data["captures"]) <= data["captureCount"]
        and len(data["diagnostics"]) <= data["diagnosticReceiptCount"],
        "native shard totals",
    )
    return data


def validate_inventory_objects(raw, provenance, objects):
    """Bind a reviewed inventory to exact supplied report and part bytes.

    No files are extracted, no historical code runs, and this does not certify
    image validity or pixel acceptance. Missing dependencies remain fatal.
    """
    import io
    import zipfile

    data = validate(raw, "inventory.json", provenance)
    a.require(data["schemaVersion"] == 2, "historical v1 inventory has no part hash closure")
    a.require(type(objects) is dict, "native dependency mapping")
    expected = {r["path"]: r for r in data["originalReports"]}
    for project in data["projects"].values():
        for part in project["parts"]:
            a.require(part["path"] not in expected, "native duplicate dependency")
            expected[part["path"]] = part
    a.require(set(objects) == set(expected), "native missing or extra dependency")
    total = 0
    for name, descriptor in expected.items():
        body = objects[name]
        a.require(type(body) is bytes, "native dependency bytes")
        total += len(body)
        a.require(total <= 6 * 1024**3, "native dependency budget")
        a.require(
            len(body) == descriptor["bytes"] and a.digest(body) == descriptor["sha256"],
            "native dependency identity",
        )
    reports = {r["path"] for r in data["originalReports"]}
    if {"source-before.json", "source-after.json"} <= reports:
        before, after, _ = validate_matrix_reports(
            objects["source-before.json"],
            objects["source-after.json"],
            objects.get("operations-visual-runner.json"),
            provenance,
        )
        a.require(before["matrix"] == data["matrix"] == after["matrix"], "native dependency matrix")
    else:
        for name in reports - {"stages.md"}:
            validate(objects[name], name, provenance)
    checked = set()
    for project in data["projects"].values():
        members = {r["path"]: r for group in ("captures", "diagnostics") for r in project[group]}
        for part in project["parts"]:
            try:
                with zipfile.ZipFile(io.BytesIO(objects[part["path"]])) as archive:
                    infos = archive.infolist()
                    names = [info.filename for info in infos]
                    a.require(
                        len(names) == len(set(names)) and set(names) == set(part["members"]),
                        "native part exact members",
                    )
                    declared_total = sum(members[name]["bytes"] for name in names)
                    a.require(declared_total <= 32 * 1024**2, "native part expansion budget")
                    for info in infos:
                        descriptor = members[info.filename]
                        a.require(
                            not info.is_dir()
                            and not info.flag_bits & 1
                            and (info.external_attr >> 16) & 0o170000 != 0o120000
                            and info.file_size == descriptor["bytes"],
                            "native part member type/size",
                        )
                        body = archive.read(info)
                        a.require(
                            len(body) == descriptor["bytes"]
                            and a.digest(body) == descriptor["sha256"],
                            "native part member identity",
                        )
                        checked.add(info.filename)
            except (zipfile.BadZipFile, RuntimeError, OSError) as error:
                raise ValueError("invalid native dependency archive") from error
    return checked


def validate_provenance_objects(shards, provenance, objects):
    """Verify a complete shard set and exact member bytes, without inferring outcomes.

    This establishes envelope/member identity and PNG decoding only. Typed receipt
    semantics and producer approval are separate mandatory registration checks.
    """
    a.require(type(shards) is list and 0 < len(shards) <= 480, "native shard set bound")
    data = [validate(raw, "provenance.json", provenance) for raw in shards]
    first = data[0]
    a.require(first["schemaVersion"] == 2, "historical HC v1 requires view-local closure")
    a.require(len(data) == first["shards"], "native missing shard")
    indices, expected = set(), {}
    for shard in data:
        a.require(shard["shard"] not in indices, "native duplicate shard")
        indices.add(shard["shard"])
        # These are original run-wide declarations, never recomputed outcomes.
        common = set(first) - {"shard", "captures", "diagnostics"}
        a.require(
            set(shard) == set(first) and all(shard[k] == first[k] for k in common),
            "native shard declaration mismatch",
        )
        for category in ("captures", "diagnostics"):
            for row in shard[category]:
                a.require(row["path"] not in expected, "native duplicate shard member")
                expected[row["path"]] = (category, row)
    a.require(indices == set(range(first["shards"])), "native shard index closure")
    a.require(
        type(objects) is dict and set(objects) == set(expected),
        "native missing or extra shard dependency",
    )
    a.require(
        sum(category == "captures" for category, _ in expected.values()) == first["captureCount"]
        and sum(category == "diagnostics" for category, _ in expected.values())
        == first["diagnosticReceiptCount"],
        "native global member count",
    )
    for suite, declaration in first["suites"].items():
        a.require(
            sum(
                category == "captures" and row["sourceRoot"] == suite
                for category, row in expected.values()
            )
            == declaration["captures"],
            "native suite capture closure",
        )
    total = 0
    dimensions = {}
    for path, (category, descriptor) in expected.items():
        body = objects[path]
        a.require(type(body) is bytes, "native shard dependency bytes")
        total += len(body)
        a.require(total <= 6 * 1024**3, "native shard dependency budget")
        a.require(
            len(body) == descriptor["bytes"] and a.digest(body) == descriptor["sha256"],
            "native shard dependency identity",
        )
        if category == "captures":
            dimensions[path] = a.png(body)
        else:
            # Reject duplicate keys now; family validation follows registration.
            a.require(type(sequence_evidence.strict_json(body)) is dict, "native diagnostic root")
    return dimensions


def hc_source_profile(repo, provenance, view):
    """Read a finite historical declaration from its Git tree, never execute it."""
    import subprocess

    a.verify_source(repo, provenance)
    path = "scripts/python/workspace_png_evidence.py"
    line = (
        subprocess.check_output(
            ["git", "ls-tree", provenance["sourceTree"], "--", path], cwd=repo, timeout=10
        )
        .decode()
        .strip()
    )
    a.require(
        line.startswith("100644 blob ") and line.split("\t", 1)[1] == path,
        "HC pinned producer blob",
    )
    oid = line.split()[2]
    size = int(subprocess.check_output(["git", "cat-file", "-s", oid], cwd=repo, timeout=10))
    a.require(0 < size <= 65536, "HC pinned producer size")
    raw = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=repo, timeout=10)
    # Reviewed complete historical blobs: declaration scanning cannot establish
    # runtime values in the presence of additional writes or indirect mutation.
    profiles = {
        (
            "3239fe849d9414f6fd2514e8e8306ef0e354277a",
            "99d0540dc7dff9c26905e987bffc47722d643a3435b323ef5e159277d34d474f",
        ): "aggregate",
        (
            "1fc39d1e54ae866112d160fc8c277102724260f7",
            "f4818f5ed06f65c70400cd72710f312db8c3919892de6c2d732c4b76a5f0e323",
        ): "pairs",
    }
    profile = profiles.get((oid, a.digest(raw)))
    a.require(profile is not None, "HC unreviewed pinned producer blob")
    a.require(view in {"records", "schema", "imports", "exports"}, "HC pinned view")
    return hc_case(profile, view)


def validate_hc_view_archive(repo, archive_raw, descriptor, provenance):
    """Close one exact historical flat ZIP, not the entire run or pixel acceptance.

    Basename resolution is allowed only inside this hash-bound ZIP and only for
    descriptors already tied to the source-pinned finite case/view producer.
    """
    import io
    import zipfile

    fields(descriptor, "artifactId archiveSha256 member sha256 bytes")
    a.require(
        type(descriptor["artifactId"]) is int and descriptor["artifactId"] > 0,
        "HC artifact identity",
    )
    a.require(
        type(archive_raw) is bytes and 0 < len(archive_raw) <= 32 * 1024**2, "HC ZIP byte bound"
    )
    a.require(
        a.digest(archive_raw) == descriptor["archiveSha256"]
        and descriptor["member"] == "provenance.json",
        "HC exact archive binding",
    )
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        a.require(
            len(names) == len(set(names)) and "provenance.json" in names and len(names) <= 5,
            "HC exact ZIP members",
        )
        a.require(sum(i.file_size for i in infos) <= 32 * 1024**2, "HC ZIP expansion bound")
        for info in infos:
            a.require(
                not info.is_dir()
                and not info.flag_bits & 1
                and (info.external_attr >> 16) & 0o170000 != 0o120000
                and "/" not in info.filename
                and "\\" not in info.filename,
                "HC flat regular member",
            )
        raw = archive.read("provenance.json")
        a.require(
            len(raw) == descriptor["bytes"] and a.digest(raw) == descriptor["sha256"],
            "HC provenance original identity",
        )
        data = validate(raw, "provenance.json", provenance)
        a.require(data["schemaVersion"] == 1, "HC original version")
        case = hc_source_profile(repo, provenance, data["view"])
        expected = {r["path"].split("/")[-1]: r for r in data["captures"]}
        a.require(
            len(expected) == len(data["captures"])
            and set(names) == {"provenance.json"} | set(expected),
            "HC view member closure",
        )
        dimensions = {}
        for name, row in expected.items():
            a.require(row["path"] == case + "/" + name, "HC source-pinned view producer")
            body = archive.read(name)
            a.require(
                len(body) == row["bytes"] and a.digest(body) == row["sha256"],
                "HC exact PNG identity",
            )
            dimensions[row["path"]] = a.png(body)
    return dict(
        scope="exact-view-local-declared-bytes-only",
        acceptance=False,
        runComplete=False,
        originalOutcome=data["workspaceOutcome"],
        dimensions=dimensions,
    )


def validate_external_descriptor(row):
    """Shared transport/retained provenance limits; neither grants acceptance."""
    fields(row, "key artifactId archiveSha256 archiveBytes chain")
    a.require(
        type(row["artifactId"]) is int
        and row["artifactId"] > 0
        and type(row["archiveBytes"]) is int
        and 0 < row["archiveBytes"] <= 32 * 1024**2,
        "external provenance archive",
    )
    digest(row["archiveSha256"])
    a.require(
        type(row["chain"]) is list and 1 <= len(row["chain"]) <= 3, "external provenance chain"
    )
    for item in row["chain"]:
        fields(item, "member bytes sha256")
        a.require(
            type(item["member"]) is str
            and len(item["member"]) <= 512
            and not item["member"].startswith(("/", "\\"))
            and "\\" not in item["member"]
            and ".." not in item["member"].split("/")
            and type(item["bytes"]) is int
            and 0 < item["bytes"] <= 32 * 1024**2,
            "external provenance member",
        )
        digest(item["sha256"])


def _validate_external_inventory_transport(repo, registry, archives):
    """External member identity only; v1 has no native-declared part closure.

    Supplied ZIP bytes are checked, never executed or extracted. This independent
    profile cannot satisfy validate_inventory_objects or native proof registration.
    """
    import io
    import zipfile

    fields(
        registry,
        "schemaVersion kind acceptance runComplete nativePartClosure provenance inventory members",
    )
    a.require(
        registry["schemaVersion"] == 4
        and type(registry["schemaVersion"]) is int
        and registry["kind"] == "external-transport-inventory-v1"
        and registry["acceptance"] is False
        and registry["runComplete"] is False
        and registry["nativePartClosure"] == "unavailable",
        "external retention profile",
    )
    provenance = registry["provenance"]
    fields(provenance, "sourceCommit sourceTree requestedHead runId attempt")
    a.verify_source(repo, provenance)
    a.require(type(archives) is dict and 0 < len(archives) <= 512, "external archive bound")
    a.require(sum(len(b) for b in archives.values()) <= 6 * 1024**3, "external total bound")
    used, locations = set(), set()
    containers = {}

    def resolve(row):
        validate_external_descriptor(row)
        body = archives.get(row["archiveSha256"])
        a.require(
            type(body) is bytes
            and type(row["archiveBytes"]) is int
            and len(body) == row["archiveBytes"]
            and 0 < len(body) <= 32 * 1024**2
            and a.digest(body) == row["archiveSha256"],
            "external archive identity",
        )
        used.add(row["archiveSha256"])
        location = (
            row["artifactId"],
            row["archiveSha256"],
            tuple(x["member"] for x in row["chain"]),
        )
        a.require(location not in locations, "external duplicate member binding")
        locations.add(location)
        prefix = ()
        for item in row["chain"]:
            try:
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    infos = archive.infolist()
                    names = [i.filename for i in infos]
                    container_key = (row["artifactId"], row["archiveSha256"], prefix)
                    if container_key not in containers:
                        containers[container_key] = (set(names), set())
                    a.require(
                        containers[container_key][0] == set(names), "external container identity"
                    )
                    containers[container_key][1].add(item["member"])
                    a.require(
                        len(names) <= 65536 and len(names) == len(set(names)),
                        "external ambiguous members",
                    )
                    a.require(
                        sum(i.file_size for i in infos) <= 32 * 1024**2, "external expansion bound"
                    )
                    for info in infos:
                        a.require(
                            not info.flag_bits & 1
                            and (info.external_attr >> 16) & 0o170000 != 0o120000,
                            "external unsafe member",
                        )
                        a.require(
                            not info.filename.startswith(("/", "\\"))
                            and "\\" not in info.filename
                            and ".." not in info.filename.split("/"),
                            "external unsafe path",
                        )
                    a.require(item["member"] in names, "external missing member")
                    info = archive.getinfo(item["member"])
                    a.require(
                        not info.is_dir() and info.file_size == item["bytes"],
                        "external member size",
                    )
                    body = archive.read(info)
            except (zipfile.BadZipFile, RuntimeError, OSError) as error:
                raise ValueError("external invalid ZIP") from error
            a.require(
                len(body) == item["bytes"] and a.digest(body) == item["sha256"],
                "external member identity",
            )
            prefix += (item["member"],)
        return body

    result = validate_external_inventory_contents(registry, resolve)
    a.require(used == set(archives), "external dependency closure")
    a.require(
        all(actual == approved for actual, approved in containers.values()),
        "external unapproved archive member",
    )
    return dict(result, externalMemberClosure=True)


def validate_external_report(raw, name, provenance):
    if name != "stages.md":
        return validate(raw, name, provenance)
    # Exact authored stage-summary grammar, not arbitrary Markdown retention.
    pattern = r"\| Stage \| Outcome \|\n\| --- \| --- \|\n"
    for stage in ("SOURCE", "INSTALL", "BROWSERS", "FONTS", "BEFORE", "MATRIX", "AFTER"):
        pattern += r"\| " + stage + r" \| (?:success|failure|skipped|cancelled|not-run) \|\n"
    pattern += re.escape(
        "\nFresh native captures require independent visual review. Declared skips are not executed checks. No whole-project or release acceptance is granted.\n"
    )
    a.require(
        type(raw) is bytes and len(raw) <= 1024 and re.fullmatch(pattern.encode(), raw),
        "external unsupported stage report",
    )
    return None


def validate_external_inventory_contents(registry, resolve):
    """Closed approved leaves; resolve must enforce the profile's byte identity."""
    provenance = registry["provenance"]
    a.require(
        registry["inventory"]["key"] == "inventory.json"
        and registry["inventory"]["chain"][-1]["member"].split("/")[-1] == "inventory.json",
        "external inventory binding",
    )
    raw = resolve(registry["inventory"])
    leaves = {"inventory.json": raw}
    data = validate(raw, "inventory.json", provenance)
    a.require(data["schemaVersion"] == 1, "external historical version")
    expected = {"reports/" + r["path"]: (r, False) for r in data["originalReports"]}
    for project, entry in data["projects"].items():
        for group in ("captures", "diagnostics"):
            for row in entry.get(group, []):
                key = project + "/" + row["path"]
                a.require(key not in expected, "external ambiguous declared object")
                expected[key] = (row, group == "captures")
    a.require(
        type(registry["members"]) is list and len(registry["members"]) == len(expected),
        "external member count",
    )
    seen, dimensions = set(), {}
    for binding in registry["members"]:
        key = binding["key"]
        a.require(key in expected and key not in seen, "external missing/extra/duplicate binding")
        seen.add(key)
        descriptor, image = expected[key]
        # Exact producer path, not an unscoped basename fallback.
        a.require(binding["chain"][-1]["member"] == descriptor["path"], "external producer member")
        body = resolve(binding)
        a.require(
            len(body) == descriptor["bytes"] and a.digest(body) == descriptor["sha256"],
            "external declared identity",
        )
        if image:
            dimensions[key] = a.png(body)
        elif key.startswith("reports/"):
            report = validate_external_report(body, descriptor["path"], provenance)
            if isinstance(report, dict) and "matrix" in report:
                a.require(report["matrix"] == data["matrix"], "external report matrix")
        else:
            # The two inspected v1 inventories declare no diagnostic leaves.
            a.require(False, "unsupported external v1 diagnostic leaf")
        leaves[key] = body
    a.require(seen == set(expected), "external leaf dependency closure")
    if {"reports/source-before.json", "reports/source-after.json"} <= set(leaves):
        before, after, _ = validate_matrix_reports(
            leaves["reports/source-before.json"],
            leaves["reports/source-after.json"],
            leaves.get("reports/operations-visual-runner.json"),
            provenance,
        )
        a.require(before["matrix"] == data["matrix"] == after["matrix"], "external report matrix")
    return dict(
        original=raw,
        data=data,
        leaves=leaves,
        nativePartClosure="unavailable",
        acceptance=False,
        runComplete=False,
        dimensions=dimensions,
    )


def validate_external_inventory_transport(repo, registry, archives):
    try:
        return _validate_external_inventory_transport(repo, registry, archives)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as error:
        raise ValueError("invalid external retention shape") from error
