"""Required configuration checks must also run for stacked feature PRs."""

from pathlib import Path

import yaml


def test_environment_sync_accepts_pull_requests_to_feature_branches():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/sync-config.yml").read_text())
    # PyYAML's YAML 1.1 loader may interpret the GitHub key `on` as boolean True.
    triggers = workflow.get("on", workflow.get(True))
    assert "pull_request" in triggers
    event = triggers["pull_request"] or {}
    assert not event.get("branches"), "Stacked PRs must not skip environment verification"
    assert not event.get("branches-ignore")


def test_environment_sync_still_fails_configuration_drift():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/sync-config.yml").read_text())
    steps = workflow["jobs"]["sync-config"]["steps"]
    failure = next(
        step for step in steps if step.get("name") == "Fail if configuration is out of sync"
    )
    assert "changes_detected == 'true'" in failure["if"]
    assert "exit 1" in failure["run"]


def test_branch_selection_regression_is_executed_by_backend_ci():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci-backend.yml").read_text())
    commands = [step.get("run", "") for step in workflow["jobs"]["backend"]["steps"]]
    assert any("scripts/tests/test_stacked_pr_ci.py" in command for command in commands)
