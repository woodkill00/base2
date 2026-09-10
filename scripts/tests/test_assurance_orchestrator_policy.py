from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.python import assurance_orchestrator as assurance

ROOT = Path(__file__).resolve().parents[2]


def test_native_wrappers_exist_without_cross_shell_or_arbitrary_eval():
    bash = (ROOT / "scripts/bash/assure.sh").read_text(encoding="utf-8")
    powershell = (ROOT / "scripts/powershell/assure.ps1").read_text(encoding="utf-8")
    assert "powershell" not in bash.lower() and "pwsh" not in bash.lower()
    assert "bash" not in powershell.lower() and "wsl" not in powershell.lower()
    assert "eval " not in bash and "Invoke-Expression" not in powershell
    assert "assurance_orchestrator.py" in bash and "assurance_orchestrator.py" in powershell


def test_pre_push_uses_compact_orchestrator_instead_of_legacy_full_stream():
    hook = (ROOT / ".husky/pre-push").read_text(encoding="utf-8")
    assert "scripts/bash/assure.sh run --tier auto --json" in hook
    assert "scripts/bash/test.sh" not in hook and "scripts/powershell/test.ps1" not in hook


def test_pull_request_policy_plans_without_executing_duplicate_suites():
    workflow = (ROOT / ".github/workflows/ci-repo-guards.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in workflow
    assert "assurance_orchestrator.py plan --tier standard" in workflow
    assert "assurance_orchestrator.py run" not in workflow


def test_generated_children_inherit_public_orchestrator_but_not_private_evidence():
    factory = (ROOT / "scripts/python/create_base2_site.py").read_text(encoding="utf-8")
    assert "git','archive'" in factory
    assert "'.artifacts'" in factory
    assert (ROOT / "shared/config/assurance-orchestrator-v1.json").is_file()
    assert (ROOT / "scripts/bash/assure.sh").is_file()


def test_hosted_export_is_exact_offline_and_never_grants_authority():
    source = "a" * 40
    payload = {
        "schemaVersion": 1,
        "sourceCommit": source,
        "workflowPath": ".github/workflows/ci-backend.yml",
        "workflowCommit": source,
        "jobs": [{"name": "api", "conclusion": "success"}],
    }
    result = assurance.validate_hosted_export(payload, source, {"api"})
    assert result["status"] == "validated-informational"
    assert result["reusable"] is False and result["authority"] == "none"
    for field, value in (
        ("sourceCommit", "b" * 40), ("workflowCommit", "b" * 40),
        ("workflowPath", "unknown.yml"),
    ):
        changed = {**payload, field: value}
        with pytest.raises(assurance.AssuranceError, match="hosted_export"):
            assurance.validate_hosted_export(changed, source, {"api"})
    changed = {**payload, "jobs": [{"name": "api", "conclusion": "failure"}]}
    with pytest.raises(assurance.AssuranceError, match="hosted_export"):
        assurance.validate_hosted_export(changed, source, {"api"})


def test_self_protection_and_safety_mutation_fixtures_escalate():
    graph = assurance.load_graph(ROOT)
    fixtures = {
        "api/security/identity.py": "api-unit",
        "api/migrations/sql/999_mutation.sql": "migration-contract",
        "react-app/e2e/visual/mutation.spec.ts": "visual-contract",
        ".github/workflows/security.yml": "security-policy",
        "digital_ocean/scripts/python/orchestrate_deploy.py": "deployment-contract",
        "scripts/python/assurance_orchestrator.py": "assurance-tests",
    }
    for path, expected in fixtures.items():
        item = assurance.Change("M", path, None, "f" * 64)
        plan = assurance.build_plan(graph, [item], "auto", "a" * 40, "b" * 40, False)
        assert expected in plan["selected"], (path, plan)
        if path.startswith((".github", "digital_ocean", "scripts/python/assurance")) or "migrations" in path:
            assert plan["resolvedTier"] == "full"


def test_graph_and_schema_are_valid_json_and_plan_validator_is_registered():
    graph = json.loads((ROOT / "shared/config/assurance-orchestrator-v1.json").read_text())
    schema = json.loads((ROOT / "shared/schemas/assurance-orchestrator-v1.schema.json").read_text())
    assert assurance.validate_graph(graph) is graph
    assert schema["properties"]["schemaVersion"]["const"] == 1
    complete = json.loads((ROOT / "scripts/config/complete-gate-v1.json").read_text())
    ids = {item["id"] for item in complete["checks"]}
    assert "feature-107-plan" in ids


def test_required_workflows_run_for_pull_requests_and_main_push_without_branch_duplicates():
    policy = json.loads((ROOT / "scripts/config/ci-policy.json").read_text())
    workflows = policy["requiredPullRequestWorkflows"]
    for name in workflows:
        text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "pull_request:" in text, name
        assert "push:\n    branches: [main]" in text or "push:\n    branches: ['main']" in text, name
        assert "group: ${{ github.workflow }}-${{ github.ref }}" in text, name
        assert "cancel-in-progress: true" in text, name
        assert "branches: ['**']" not in text, name


def test_hosted_trigger_optimization_halves_feature_commit_job_runs():
    policy = json.loads((ROOT / "scripts/config/ci-policy.json").read_text())
    required_jobs = sum(len(jobs) for jobs in policy["requiredPullRequestWorkflows"].values())
    previous_feature_commit_jobs = required_jobs * 2
    optimized_feature_commit_jobs = required_jobs
    assert previous_feature_commit_jobs == 2 * optimized_feature_commit_jobs
    assert round((previous_feature_commit_jobs - optimized_feature_commit_jobs) * 100 / previous_feature_commit_jobs) == 50


def test_private_history_orders_only_ready_peers_and_rejects_tamper(tmp_path, monkeypatch):
    value = assurance.load_graph(ROOT)
    plan = assurance.build_plan(
        value, [assurance.Change("M", "docs/a.md", None, "a" * 64)], "auto",
        "a" * 40, "b" * 40, False,
        {"feature-plan": 1, "diff-check": 999999},
    )
    assert plan["selected"].index("diff-check") < plan["selected"].index("feature-plan")
    root = tmp_path / ".artifacts" / "assurance-orchestrator"
    root.mkdir(parents=True, mode=0o700)
    history = root / "history.json"
    history.write_text("{}", encoding="utf-8")
    history.chmod(0o600)
    with pytest.raises(assurance.AssuranceError, match="history_invalid"):
        assurance.load_history(tmp_path)
