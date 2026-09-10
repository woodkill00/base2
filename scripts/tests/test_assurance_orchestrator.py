from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
import jsonschema

from scripts.python import assurance_orchestrator as assurance


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def stable_source(monkeypatch):
    monkeypatch.setattr(assurance, "_source_matches_plan", lambda *_args: True)


def graph():
    return assurance.load_graph(ROOT)


def change(path: str, *, old_path: str | None = None, status: str = "M"):
    return assurance.Change(status=status, path=path, old_path=old_path, content_digest="a" * 64)


def test_graph_is_closed_acyclic_and_uses_only_fixed_commands():
    value = graph()
    assert value["tierOrder"] == ["focused", "standard", "full", "release"]
    assert set(item["commandId"] for item in value["checks"].values()) <= set(assurance.COMMANDS)
    changed = json.loads(json.dumps(value))
    changed["checks"]["diff-check"]["commandId"] = "bash -lc arbitrary"
    with pytest.raises(assurance.AssuranceError, match="command_unknown"):
        assurance.validate_graph(changed)
    changed = json.loads(json.dumps(value))
    changed["checks"]["diff-check"]["dependsOn"] = ["feature-plan"]
    changed["checks"]["feature-plan"]["dependsOn"] = ["diff-check"]
    with pytest.raises(assurance.AssuranceError, match="cycle"):
        assurance.validate_graph(changed)


def test_diff_check_admits_markdown_hard_breaks_but_rejects_conflict_markers(tmp_path):
    command = assurance.COMMANDS["diff-check"]
    assert "core.whitespace=-blank-at-eol,-blank-at-eof,space-before-tab,tab-in-indent" in command.argv
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("intentional hard break  \n", encoding="utf-8")
    argv = [base if item == "{base}" else item for item in command.argv]
    assert subprocess.run(argv, cwd=tmp_path, capture_output=True).returncode == 0
    (tmp_path / "README.md").write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n", encoding="utf-8")
    assert subprocess.run(argv, cwd=tmp_path, capture_output=True).returncode != 0


def test_docs_are_focused_while_risky_and_unknown_changes_escalate():
    value = graph()
    docs = assurance.build_plan(value, [change("docs/TESTING.md")], "auto", "a" * 40, "b" * 40, False)
    assert docs["resolvedTier"] == "focused"
    assert "diff-check" in docs["selected"] and "api-unit" not in docs["selected"]
    migration = assurance.build_plan(
        value, [change("api/migrations/sql/099_change.sql")], "auto", "a" * 40, "b" * 40, False
    )
    assert migration["resolvedTier"] == "full" and "migration-contract" in migration["selected"]
    unknown = assurance.build_plan(value, [change("mystery.bin")], "auto", "a" * 40, "b" * 40, False)
    assert unknown["resolvedTier"] == "full"
    assert any(reason.startswith("unmapped_path:") for reason in unknown["reasons"])


def test_sensitive_paths_are_case_insensitive_and_always_full_security():
    for path in ("api/auth/tokens.py", "react-app/src/contexts/AuthContext.js"):
        plan = assurance.build_plan(graph(), [change(path)], "auto", "a" * 40, "b" * 40, False)
        assert plan["resolvedTier"] == "full"
        assert "security-policy" in plan["selected"]


def test_transitive_mapping_and_requested_tier_never_downgrade():
    value = graph()
    plan = assurance.build_plan(
        value, [change("react-app/e2e/operations/example.spec.ts")], "focused", "a" * 40, "b" * 40, False
    )
    assert plan["resolvedTier"] == "standard"
    assert {"visual-contract", "frontend-unit", "contract-policy"} <= set(plan["selected"])
    full = assurance.build_plan(value, [change("docs/a.md")], "full", "a" * 40, "b" * 40, False)
    assert full["resolvedTier"] == "full"
    assert set(value["mandatoryChecks"]["full"]) <= set(full["selected"])


def test_rename_uses_both_paths_and_test_policy_self_protects():
    value = graph()
    renamed = assurance.build_plan(
        value,
        [change("docs/new.md", old_path="api/security/identity.py", status="R100")],
        "auto", "a" * 40, "b" * 40, False,
    )
    assert "api-unit" in renamed["selected"]
    tests = assurance.build_plan(
        value, [change("scripts/tests/test_anything.py")], "auto", "a" * 40, "b" * 40, False
    )
    assert tests["resolvedTier"] in {"standard", "full"}
    assert "assurance-tests" in tests["selected"]


def test_release_is_exact_complete_gate_only_and_dirty_release_is_denied():
    value = graph()
    clean = assurance.build_plan(value, [change("docs/a.md")], "release", "a" * 40, "b" * 40, False)
    assert clean["selected"] == ["complete-gate"]
    dirty = assurance.build_plan(value, [change("docs/a.md")], "release", "a" * 40, "b" * 40, True)
    with pytest.raises(assurance.AssuranceError, match="dirty_strong_tier"):
        assurance.require_executable_plan(dirty)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()


def test_change_collection_binds_dirty_content_and_rejects_bad_base(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "docs" / "a.md").write_text("two\n", encoding="utf-8")
    changes = assurance.collect_changes(tmp_path, base)
    assert changes.dirty is True and changes.base_commit == base
    assert changes.entries[0].content_digest == hashlib.sha256(b"two\n").hexdigest()
    with pytest.raises(assurance.AssuranceError, match="base_invalid"):
        assurance.collect_changes(tmp_path, "not-a-sha")


def test_compact_output_is_bounded_and_contains_honest_residual_scope():
    plan = assurance.build_plan(graph(), [change("docs/a.md")], "auto", "a" * 40, "b" * 40, False)
    rendered = assurance.compact_json({**plan, "status": "planned", "evidencePath": None})
    assert len(rendered.encode()) <= 4096
    assert len(rendered.splitlines()) <= 40
    payload = json.loads(rendered)
    assert payload["resolvedTier"] == "focused" and payload["avoided"]
    text = assurance.compact_text({"status": "passed", "resolvedTier": "focused", "executed": ["diff-check"]})
    assert text.startswith("Assurance: PASSED\n") and "Executed: diff-check" in text


def test_token_estimate_and_benchmark_do_not_count_estimates_as_measurements():
    assert assurance.estimate_tokens(0) == 0
    assert assurance.estimate_tokens(4096) == 1024
    report = assurance.benchmark_report(
        legacy_measured_ms=1000, optimized_measured_ms=400,
        legacy_output_bytes=10000, optimized_output_bytes=800,
        estimated_avoided_ms=9000, mutations_detected=7, mutations_total=7,
    )
    assert report["timeReductionPercent"] == 60
    assert report["outputReductionPercent"] == 92
    assert report["status"] == "passed"
    with pytest.raises(assurance.AssuranceError, match="benchmark_measurement"):
        assurance.benchmark_report(
            legacy_measured_ms=0, optimized_measured_ms=0, legacy_output_bytes=1,
            optimized_output_bytes=1, estimated_avoided_ms=100, mutations_detected=1,
            mutations_total=1,
        )


def test_public_cli_rejects_commands_paths_environment_and_exclusions():
    parser = assurance.parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--command", "rm"])
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--exclude", "security-policy"])
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--env", "TOKEN=x"])


def _focused_plan():
    return assurance.build_plan(graph(), [change("docs/a.md")], "auto", "a" * 40, "b" * 40, False)


def test_execution_is_compact_private_and_exact_replay_safe(tmp_path, monkeypatch):
    monkeypatch.setitem(
        assurance.COMMANDS, "diff-check",
        assurance.Command(("python3", "-c", "print('ok')"), timeout=10),
    )
    monkeypatch.setitem(
        assurance.COMMANDS, "feature-plan",
        assurance.Command(("python3", "-c", "print('ok')"), timeout=10),
    )
    value = graph()
    plan = _focused_plan()
    first = assurance.execute_plan(tmp_path, value, plan)
    assert first["status"] == "passed" and first["executed"] == ["diff-check", "feature-plan"]
    assert first["outputBytes"] <= 4096 and first["estimatedTokens"] <= 1024
    result_path = tmp_path / first["evidencePath"]
    assert result_path.is_file() and result_path.stat().st_mode & 0o077 == 0
    second = assurance.execute_plan(tmp_path, value, plan)
    assert second["executed"] == [] and second["reused"] == ["diff-check", "feature-plan"]
    assert assurance.latest_status(tmp_path)["planDigest"] == plan["planDigest"]


def test_exact_complete_gate_requires_exact_manifest_inventory(tmp_path, monkeypatch):
    commit = "a" * 40
    run = tmp_path / ".artifacts" / "complete-gate" / "20260910T120000Z-1"
    run.mkdir(parents=True, mode=0o700)
    (tmp_path / ".artifacts").chmod(0o700)
    (tmp_path / ".artifacts" / "complete-gate").chmod(0o700)
    config = tmp_path / "scripts" / "config"
    config.mkdir(parents=True)
    manifest = {"schemaVersion": 1, "checks": [
        {"id": "first", "command": ["true"], "required": True, "timeoutSeconds": 1, "dependsOn": [], "requiredTools": []},
        {"id": "second", "command": ["true"], "required": False, "timeoutSeconds": 1, "dependsOn": ["first"], "requiredTools": []},
    ]}
    (config / "complete-gate-v1.json").write_text(json.dumps(manifest), encoding="utf-8")
    payload = {"schemaVersion": 1, "sourceCommit": commit, "overallStatus": "passed", "checks": [
        {"id": "first", "required": True, "status": "passed"},
    ]}
    result = run / "result.json"
    result.write_text(json.dumps(payload), encoding="utf-8")
    result.chmod(0o600)
    monkeypatch.setattr(assurance, "validate_gate_evidence", lambda *_args: json.loads(result.read_text()))
    assert assurance.exact_complete_gate_evidence(tmp_path, commit) is None
    payload["checks"].append({"id": "second", "required": False, "status": "passed"})
    result.write_text(json.dumps(payload), encoding="utf-8")
    plan = assurance.build_plan(graph(), [change("docs/a.md")], "auto", commit, commit, False)
    executed = assurance.execute_plan(tmp_path, graph(), plan)
    assert executed["status"] == "passed" and executed["executed"] == []
    assert executed["reused"] == ["complete-gate"] and executed["resolvedTier"] == "focused"
    assert executed["satisfiedBy"] == "exact-complete-gate"
    assert executed["outputBytes"] > 0 and executed["estimatedTokens"] > 0
    payload["checks"][0]["status"] = "failed"
    result.write_text(json.dumps(payload), encoding="utf-8")
    assert assurance.exact_complete_gate_evidence(tmp_path, commit) is None


def test_explicit_release_always_executes_even_with_strong_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(assurance, "exact_complete_gate_evidence", lambda *_args: "strong.json")
    monkeypatch.setitem(assurance.COMMANDS, "complete-gate", assurance.Command(("python3", "-c", "print('ok')")))
    plan = assurance.build_plan(graph(), [change("docs/a.md")], "release", "a" * 40, "b" * 40, False)
    result = assurance.execute_plan(tmp_path, graph(), plan)
    assert result["executed"] == ["complete-gate"] and result["reused"] == []


def test_execution_fails_fast_redacts_and_blocks_remaining_checks(tmp_path, monkeypatch):
    monkeypatch.setitem(
        assurance.COMMANDS, "diff-check",
        assurance.Command(("python3", "-c", "print('TOKEN=very-secret-value');raise SystemExit(1)"), timeout=10),
    )
    value = graph()
    result = assurance.execute_plan(tmp_path, value, _focused_plan())
    assert result["status"] == "failed" and result["failed"] == ["diff-check"]
    assert result["blocked"] == ["feature-plan"]
    run = json.loads((tmp_path / result["evidencePath"]).read_text(encoding="utf-8"))
    log = next((tmp_path / result["evidencePath"]).parent.glob("*.log")).read_text()
    assert "very-secret-value" not in log
    assert "[REDACTED]" in log and "very-secret-value" not in json.dumps(run)
    assert result["failureDetails"][0]["attempts"] == 1
    assert result["failureDetails"][0]["exitCode"] == 1
    assert "very-secret-value" not in result["failureDetails"][0]["summary"]


def test_linked_evidence_parent_is_rejected_without_external_write(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".artifacts").symlink_to(outside, target_is_directory=True)
    with pytest.raises((ValueError, OSError, assurance.AssuranceError)):
        assurance.execute_plan(tmp_path, graph(), _focused_plan())
    assert list(outside.iterdir()) == []


def test_tampered_cache_is_not_reused(tmp_path, monkeypatch):
    monkeypatch.setitem(
        assurance.COMMANDS, "diff-check",
        assurance.Command(("python3", "-c", "print('ok')"), timeout=10),
    )
    monkeypatch.setitem(
        assurance.COMMANDS, "feature-plan",
        assurance.Command(("python3", "-c", "print('ok')"), timeout=10),
    )
    value = graph()
    plan = _focused_plan()
    assurance.execute_plan(tmp_path, value, plan)
    cache = tmp_path / ".artifacts" / "assurance-orchestrator" / "cache"
    next(cache.rglob("result.json")).write_text("{}", encoding="utf-8")
    with pytest.raises(assurance.AssuranceError, match="cache_invalid"):
        assurance.execute_plan(tmp_path, value, plan)


def test_large_change_explanation_remains_bounded_and_digest_bound():
    changes = [change(f"docs/item-{index}.md") for index in range(500)]
    plan = assurance.build_plan(graph(), changes, "auto", "a" * 40, "b" * 40, False)
    assert plan["reasonCount"] == 500 and len(plan["reasons"]) == 12
    assert len(plan["reasonsDigest"]) == 64
    assert len(assurance.compact_json({**plan, "status": "planned", "evidencePath": None}).encode()) <= 4096


def test_global_visual_sources_require_full_visual_matrix():
    value = graph()
    for path in ("react-app/src/index.css", "react-app/src/components/glass/GlassCard.tsx"):
        plan = assurance.build_plan(value, [change(path)], "auto", "a" * 40, "b" * 40, False)
        assert plan["resolvedTier"] == "full"
        assert "visual-full" in plan["selected"]


def test_dirty_focused_runs_never_read_or_write_cache(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))
    monkeypatch.setitem(assurance.COMMANDS, "feature-plan", assurance.Command(("python3", "-c", "pass")))
    plan = assurance.build_plan(graph(), [change("docs/a.md")], "auto", "a" * 40, "b" * 40, True)
    first = assurance.execute_plan(tmp_path, graph(), plan)
    second = assurance.execute_plan(tmp_path, graph(), plan)
    assert first["executed"] == second["executed"] == ["diff-check", "feature-plan"]
    assert first["reused"] == second["reused"] == []


def test_private_incomplete_cache_stage_is_recovered(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))
    monkeypatch.setitem(assurance.COMMANDS, "feature-plan", assurance.Command(("python3", "-c", "pass")))
    cache = tmp_path / ".artifacts" / "assurance-orchestrator" / "cache"
    cache.mkdir(parents=True, mode=0o700)
    stage = cache / ("." + "a" * 64 + "." + "b" * 32)
    stage.mkdir(mode=0o700)
    member = stage / "output.log"
    member.write_text("partial", encoding="utf-8")
    member.chmod(0o600)
    result = assurance.execute_plan(tmp_path, graph(), _focused_plan())
    assert result["status"] == "passed" and not stage.exists()


def test_interrupted_run_is_visible_and_never_a_pass(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))

    def interrupted(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(assurance.subprocess, "run", interrupted)
    with pytest.raises(KeyboardInterrupt):
        assurance.execute_plan(tmp_path, graph(), _focused_plan())
    status = assurance.latest_status(tmp_path)
    assert status["status"] == "interrupted" and status["current"] is False


def test_run_lease_returns_distinct_busy_error(tmp_path):
    with assurance._run_lease(tmp_path):
        with pytest.raises(assurance.AssuranceError, match="run_busy"):
            assurance.execute_plan(tmp_path, graph(), _focused_plan())


def test_toolchain_identity_changes_cache_input(monkeypatch):
    plan = _focused_plan()
    value = graph()
    monkeypatch.setattr(assurance, "_executable_identity", lambda *_args: {"sha256": "a" * 64})
    first = assurance._input_digest("diff-check", plan, value, ROOT)
    monkeypatch.setattr(assurance, "_executable_identity", lambda *_args: {"sha256": "b" * 64})
    assert assurance._input_digest("diff-check", plan, value, ROOT) != first


def test_managed_python_distribution_drift_changes_cache_input(monkeypatch):
    plan = _focused_plan()
    value = graph()
    monkeypatch.setitem(
        assurance.COMMANDS, "diff-check",
        assurance.Command((".venv/bin/python", "-c", "pass")),
    )
    monkeypatch.setattr(
        assurance, "_python_distribution_identity",
        lambda *_args: {"count": 1, "sha256": "a" * 64},
    )
    first = assurance._input_digest("diff-check", plan, value, ROOT)
    monkeypatch.setattr(
        assurance, "_python_distribution_identity",
        lambda *_args: {"count": 1, "sha256": "b" * 64},
    )
    assert assurance._input_digest("diff-check", plan, value, ROOT) != first


def test_node_installed_lock_drift_changes_cache_input(tmp_path, monkeypatch):
    project = tmp_path / "project"
    lock = project / "react-app" / "node_modules" / ".package-lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text('{"version":1}', encoding="utf-8")
    monkeypatch.setattr(assurance, "_resolve_named_executable", lambda _name: Path("/usr/bin/node"))
    command = assurance.Command(("node", "example.js"), cwd="react-app")
    first = assurance._runtime_dependency_identity("frontend-unit", command, project)
    lock.write_text('{"version":2}', encoding="utf-8")
    second = assurance._runtime_dependency_identity("frontend-unit", command, project)
    assert first != second
    lock.unlink()
    lock.symlink_to(project / "outside.json")
    with pytest.raises(assurance.AssuranceError, match="dependency_manifest"):
        assurance._runtime_dependency_identity("frontend-unit", command, project)


def test_playwright_path_is_explicit_only_when_safely_admitted(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cache = home / ".cache"
    browsers = cache / "ms-playwright"
    browsers.mkdir(parents=True)
    cache.chmod(0o700)
    browsers.chmod(0o755)
    monkeypatch.setattr(assurance.Path, "home", classmethod(lambda cls: home))
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    environment = assurance._environment(isolated, "visual-contract")
    assert environment["HOME"] == str(isolated)
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == str(browsers)
    browsers.chmod(0o777)
    with pytest.raises(assurance.AssuranceError, match="playwright_browser_path_unsafe"):
        assurance._environment(isolated, "visual-contract")


def test_repository_paths_reject_escape_controls_and_windows_separators():
    for value in ("../outside", "/absolute", "bad\nname", "windows\\path", ""):
        with pytest.raises(assurance.AssuranceError, match="change_path_invalid"):
            assurance._normalize_repo_path(value)


def test_ambient_path_cannot_shadow_approved_executable(tmp_path, monkeypatch):
    fake = tmp_path / "python3"
    fake.write_text("malicious", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    resolved = assurance._resolve_named_executable("python3")
    assert resolved != fake and str(resolved).startswith(("/usr/", "/bin/"))


def test_managed_python_keeps_absolute_venv_launcher_and_rejects_other_links():
    managed = assurance._resolve_executable(assurance.COMMANDS["assurance-tests"], ROOT)
    assert managed == ROOT / ".venv/bin/python"
    assert managed.resolve() != managed
    with pytest.raises(assurance.AssuranceError, match="tool_unsafe"):
        assurance._resolve_executable(assurance.Command((".venv/bin/pip",)), ROOT)


def test_timeout_is_single_attempt_and_blocks_following_checks(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))
    calls = 0

    def timeout(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise subprocess.TimeoutExpired(["python3"], 1, output=b"timed out")

    monkeypatch.setattr(assurance.subprocess, "run", timeout)
    result = assurance.execute_plan(tmp_path, graph(), _focused_plan())
    assert calls == 1 and result["failed"] == ["diff-check"]
    assert result["blocked"] == ["feature-plan"]


def test_only_exact_native_corruption_gets_one_bounded_retry(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))
    monkeypatch.setitem(assurance.COMMANDS, "feature-plan", assurance.Command(("python3", "-c", "pass")))
    outcomes = iter([
        subprocess.CompletedProcess([], -11, b"Segmentation fault", b""),
        subprocess.CompletedProcess([], 0, b"recovered", b""),
        subprocess.CompletedProcess([], 1, b"ordinary failure", b""),
    ])
    calls = 0

    def run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return next(outcomes)

    monkeypatch.setattr(assurance.subprocess, "run", run)
    result = assurance.execute_plan(tmp_path, graph(), _focused_plan())
    assert calls == 3
    assert result["failed"] == ["feature-plan"]
    receipts = json.loads((tmp_path / result["evidencePath"]).read_text())["receipts"]
    assert receipts[0]["attempts"] == 2
    assert receipts[1]["attempts"] == 1


def test_executable_identity_drift_fails_the_check(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))
    identities = iter([
        {"path": "/usr/bin/python3", "bytes": 1, "sha256": "a" * 64},
        {"path": "/usr/bin/python3", "bytes": 1, "sha256": "b" * 64},
    ])
    monkeypatch.setattr(assurance, "_executable_identity", lambda *_args: next(identities))
    result = assurance.execute_plan(tmp_path, graph(), _focused_plan())
    assert result["failed"] == ["diff-check"]
    receipt = json.loads((tmp_path / result["evidencePath"]).read_text())["receipts"][0]
    assert receipt["exitCode"] == 125


def test_repository_source_drift_fails_before_cache_publication(tmp_path, monkeypatch):
    monkeypatch.setitem(assurance.COMMANDS, "diff-check", assurance.Command(("python3", "-c", "pass")))
    states = iter((True, False))
    monkeypatch.setattr(assurance, "_source_matches_plan", lambda *_args: next(states))
    result = assurance.execute_plan(tmp_path, graph(), _focused_plan())
    assert result["failed"] == ["diff-check"]
    receipt = json.loads((tmp_path / result["evidencePath"]).read_text())["receipts"][0]
    assert receipt["exitCode"] == 125
    cache = tmp_path / ".artifacts" / "assurance-orchestrator" / "cache"
    assert list(cache.iterdir()) == []


def test_private_evidence_retention_is_bounded_and_rejects_links(tmp_path):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    for index in range(4):
        child = parent / ("a" * 63 + str(index))
        child.mkdir(mode=0o700)
        member = child / "result.json"
        member.write_text("{}")
        member.chmod(0o600)
    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assurance._prune_private_directories(descriptor, assurance.re.compile(r"[a-z0-9]{64}"), 2)
    finally:
        os.close(descriptor)
    assert len(list(parent.iterdir())) == 2
    linked = parent / ("b" * 64)
    linked.symlink_to(tmp_path, target_is_directory=True)
    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(assurance.AssuranceError, match="evidence_directory_unsafe"):
            assurance._prune_private_directories(descriptor, assurance.re.compile(r"[a-z0-9]{64}"), 2)
    finally:
        os.close(descriptor)


def test_published_graph_schema_rejects_nested_unknown_fields():
    schema = json.loads((ROOT / "shared/schemas/assurance-orchestrator-v1.schema.json").read_text())
    jsonschema.validate(graph(), schema)
    changed = json.loads(json.dumps(graph()))
    changed["checks"]["diff-check"]["command"] = ["rm", "-rf", "/"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(changed, schema)
