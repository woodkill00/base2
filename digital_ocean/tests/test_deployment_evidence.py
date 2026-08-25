from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from digital_ocean.scripts.python.deployment_evidence import (
    EvidenceIntegrityError,
    EvidenceRun,
    EvidenceStore,
    EvidenceValidationError,
)

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def base_evidence(**overrides):
    item = {
        "schemaVersion": 1,
        "runId": "run-test-001",
        "leaseId": "lease-test-001",
        "sourceCommit": "a" * 40,
        "manifestDigest": "b" * 64,
        "action": "deploy",
        "status": "running",
        "startedAt": "2026-08-24T20:00:00Z",
        "finishedAt": None,
        "stages": [],
        "cost": {
            "currency": "USD",
            "ceilingMinorUnits": 100,
            "projectedMinorUnits": 10,
            "actualMinorUnits": 0,
            "withinBudget": True,
        },
        "artifacts": [],
        "failure": None,
    }
    item.update(overrides)
    return item


def test_atomic_roundtrip_and_integrity(tmp_path):
    store = EvidenceStore(tmp_path)
    created = store.create(base_evidence())
    assert store.load("run-test-001") == created
    path = tmp_path / "run-test-001.json"
    assert path.stat().st_mode & 0o777 == 0o600
    envelope = json.loads(path.read_text())
    envelope["evidence"]["action"] = "teardown"
    path.write_text(json.dumps(envelope))
    with pytest.raises(EvidenceIntegrityError, match="digest"):
        store.load("run-test-001")


def test_every_stage_can_emit_terminal_failure(tmp_path):
    for index, stage in enumerate(("admission", "provision", "dns", "health", "teardown")):
        store = EvidenceStore(tmp_path / str(index))
        run_id = f"run-stage-{index:03d}"
        store.create(base_evidence(runId=run_id))
        store.start_stage(run_id, stage, now=NOW)
        final = store.finish_failure(
            run_id, stage=stage, code="injected_failure", retryable=False, now=NOW
        )
        assert final["status"] == "failed"
        assert final["failure"] == {"stage": stage, "code": "injected_failure", "retryable": False}
        assert final["stages"][-1]["status"] == "failed"


def test_cost_ceiling_and_consistency_fail_closed(tmp_path):
    store = EvidenceStore(tmp_path)
    over = store.create(
        base_evidence(
            cost={
                "currency": "USD",
                "ceilingMinorUnits": 5,
                "projectedMinorUnits": 6,
                "actualMinorUnits": 0,
                "withinBudget": False,
            }
        )
    )
    with pytest.raises(EvidenceValidationError, match="budget"):
        store.require_budget(over)
    with pytest.raises(EvidenceValidationError, match="withinBudget"):
        store.create(
            base_evidence(
                cost={
                    "currency": "USD",
                    "ceilingMinorUnits": 100,
                    "projectedMinorUnits": 10,
                    "actualMinorUnits": 0,
                    "withinBudget": False,
                }
            )
        )


@pytest.mark.parametrize("secret", ["DO_API_TOKEN", "password", "clientSecret", "private_key"])
def test_secret_keys_are_rejected_recursively(tmp_path, secret):
    item = base_evidence()
    item["stages"] = [
        {
            "id": "admission",
            "status": "failed",
            "startedAt": "2026-08-24T20:00:00Z",
            "finishedAt": "2026-08-24T20:00:01Z",
            "diagnosticCode": {secret: "value"},
        }
    ]
    with pytest.raises(EvidenceValidationError, match="secret"):
        EvidenceStore(tmp_path).create(item)


def test_artifact_digest_size_and_names_are_strict(tmp_path):
    item = base_evidence(artifacts=[{"name": "../secret.env", "sha256": "a" * 64, "size": 1}])
    with pytest.raises(EvidenceValidationError, match="artifact name"):
        EvidenceStore(tmp_path).create(item)


def test_success_requires_finished_stages_and_cost(tmp_path):
    store = EvidenceStore(tmp_path)
    store.create(base_evidence())
    store.start_stage("run-test-001", "admission", now=NOW)
    with pytest.raises(EvidenceValidationError, match="running stage"):
        store.finish_success("run-test-001", actual_minor_units=5, now=NOW)
    store.finish_stage("run-test-001", "admission", "passed", now=NOW)
    result = store.finish_success("run-test-001", actual_minor_units=5, now=NOW)
    assert result["status"] == "passed"
    assert result["cost"]["actualMinorUnits"] == 5


def test_evidence_run_records_success_and_failure(tmp_path):
    times = iter(datetime(2026, 8, 24, 20, 0, second=value, tzinfo=UTC) for value in range(8))
    store = EvidenceStore(tmp_path)
    run = EvidenceRun(store, base_evidence(), clock=lambda: next(times))
    assert run.execute("admission", lambda: "ok", failure_code="admission_failed") == "ok"
    final = run.complete(actual_minor_units=4)
    assert final["status"] == "passed"
    assert final["stages"][0]["status"] == "passed"

    failed_store = EvidenceStore(tmp_path / "failed")
    failed = EvidenceRun(
        failed_store,
        base_evidence(runId="run-failed-001"),
        clock=lambda: next(times),
    )
    with pytest.raises(RuntimeError, match="injected"):
        failed.execute(
            "dns",
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            failure_code="dns_failed",
        )
    receipt = failed_store.load("run-failed-001")
    assert receipt["status"] == "failed"
    assert receipt["stages"][0]["status"] == "failed"


def test_strict_evidence_validator_rejects_malformed_shapes(tmp_path):
    valid_stage = {
        "id": "admission",
        "status": "passed",
        "startedAt": "2026-08-24T20:00:00Z",
        "finishedAt": "2026-08-24T20:00:01Z",
        "diagnosticCode": None,
    }
    valid_artifact = {"name": "receipt.json", "sha256": "c" * 64, "size": 1}
    valid_failure = {"stage": "dns", "code": "dns_failed", "retryable": False}
    cases = []

    def add(expected, change):
        item = deepcopy(base_evidence())
        change(item)
        cases.append((expected, item))

    add("unknown field", lambda item: item.update(extra=True))
    add("missing field", lambda item: item.pop("action"))
    add("schemaVersion", lambda item: item.update(schemaVersion=2))
    add("runId is unsafe", lambda item: item.update(runId="../bad"))
    add("sourceCommit", lambda item: item.update(sourceCommit="bad"))
    add("manifestDigest", lambda item: item.update(manifestDigest="bad"))
    add("action or status", lambda item: item.update(action="destroy-everything"))
    add("valid date-time", lambda item: item.update(startedAt="not-a-date"))
    add("timezone", lambda item: item.update(startedAt="2026-08-24T20:00:00"))
    add("running evidence", lambda item: item.update(finishedAt="2026-08-24T20:00:01Z"))
    add(
        "terminal evidence",
        lambda item: item.update(status="passed", finishedAt=None),
    )
    add(
        "precedes",
        lambda item: item.update(status="passed", finishedAt="2026-08-24T19:00:00Z"),
    )
    add("stages must", lambda item: item.update(stages={}))
    add("stage must", lambda item: item.update(stages=["bad"]))
    add(
        "stage id",
        lambda item: item.update(stages=[{**valid_stage, "id": "../bad"}]),
    )
    add("duplicated", lambda item: item.update(stages=[valid_stage, valid_stage]))
    add(
        "stage status",
        lambda item: item.update(stages=[{**valid_stage, "status": "unknown"}]),
    )
    add(
        "running stage",
        lambda item: item.update(
            stages=[{**valid_stage, "status": "running", "finishedAt": valid_stage["finishedAt"]}]
        ),
    )
    add(
        "terminal stage",
        lambda item: item.update(stages=[{**valid_stage, "finishedAt": None}]),
    )
    add(
        "diagnosticCode",
        lambda item: item.update(stages=[{**valid_stage, "diagnosticCode": 7}]),
    )
    add("cost must", lambda item: item.update(cost=[]))
    add("currency", lambda item: item["cost"].update(currency="usd"))
    add("MinorUnits", lambda item: item["cost"].update(actualMinorUnits=True))
    add("artifacts must", lambda item: item.update(artifacts={}))
    add("artifact must", lambda item: item.update(artifacts=["bad"]))
    add("duplicated", lambda item: item.update(artifacts=[valid_artifact, valid_artifact]))
    add(
        "artifact digest",
        lambda item: item.update(artifacts=[{**valid_artifact, "sha256": "bad"}]),
    )
    add(
        "artifact size",
        lambda item: item.update(artifacts=[{**valid_artifact, "size": -1}]),
    )
    add("failure must", lambda item: item.update(failure="bad"))
    add(
        "failure fields",
        lambda item: item.update(
            status="failed",
            finishedAt="2026-08-24T20:00:01Z",
            failure={**valid_failure, "code": ""},
        ),
    )
    add(
        "retryable",
        lambda item: item.update(
            status="failed",
            finishedAt="2026-08-24T20:00:01Z",
            failure={**valid_failure, "retryable": "no"},
        ),
    )
    add(
        "requires failure",
        lambda item: item.update(status="failed", finishedAt="2026-08-24T20:00:01Z"),
    )
    add("non-failed", lambda item: item.update(failure=valid_failure))

    for index, (expected, item) in enumerate(cases):
        with pytest.raises(EvidenceValidationError, match=expected):
            EvidenceStore(tmp_path / str(index)).create(item)
