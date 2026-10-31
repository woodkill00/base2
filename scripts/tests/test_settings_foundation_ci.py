"""Keep identity boundaries, browser diagnostics and their blocking CI gates intact."""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
BROWSER_SUITES = {
    "ACCOUNT": "account_acceptance",
    "SETTINGS": "settings_acceptance",
    "WORKSPACE": "workspace_acceptance",
    "LAYOUT": "layout_acceptance",
    "VOLCANO": "volcano_acceptance",
    "JOURNEYS": "journeys_acceptance",
    "MODULE_JOURNEYS": "module_journeys_acceptance",
}
PREREQUISITES = ("install", "build", "browsers", "fonts")


def frontend_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci-frontend.yml").read_text())
    return workflow["jobs"]["frontend"]["steps"]


def test_identity_audit_gate_uses_isolated_postgres_and_real_runner():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci-backend.yml").read_text())
    job = workflow["jobs"]["identity-postgres-acceptance"]
    assert "if" not in job
    assert "@sha256:" in job["services"]["postgres"]["image"]
    assert job["env"]["DB_NAME"] == "base2_identity_test"
    assert job["services"]["postgres"]["env"]["POSTGRES_DB"] == job["env"]["DB_NAME"]
    runner = next(
        step
        for step in job["steps"]
        if step.get("name") == "Verify organization audit boundaries on real PostgreSQL"
    )
    assert runner["run"] == "python scripts/python/run_identity_postgres_checks.py"
    assert "continue-on-error" not in runner
    assert "if" not in runner
    persistence = next(
        step
        for step in job["steps"]
        if step.get("name") == "Verify settings persistence and concurrent saves on real PostgreSQL"
    )
    assert persistence["run"] == (
        "python -m pytest -c api/pytest.ini --no-cov -m integration "
        "api/tests/test_settings_postgres.py"
    )
    assert "if" not in persistence
    assert "continue-on-error" not in persistence


def test_settings_browser_evidence_is_separate_and_retained_on_failure():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci-frontend.yml").read_text())
    steps = workflow["jobs"]["frontend"]["steps"]
    commands = [step.get("run", "") for step in steps]
    assert "npm run test:account-e2e -- --output=../.artifacts/settings-121/account" in commands
    assert (
        "npm run test:settings-release -- --output=../.artifacts/settings-121/release" in commands
    )
    upload = next(
        step for step in steps if step.get("name") == "Upload settings acceptance evidence"
    )
    assert upload["if"].startswith("always()")
    assert upload["with"]["path"] == ".artifacts/settings-121"


def test_workspace_release_matrix_runs_and_retains_its_own_evidence():
    steps = frontend_steps()
    step = next(item for item in steps if item.get("id") == "workspace_acceptance")
    assert step["run"] == ("npm run test:workspace-release -- --output=../.artifacts/workspace-124")
    upload = next(
        item for item in steps if item.get("name") == "Upload workspace acceptance evidence"
    )
    assert upload["if"] == "always() && steps.scope.outputs.mode == 'full'"
    assert upload["with"]["path"] == ".artifacts/workspace-124"
    assert upload["with"]["name"] == "workspace-124"
    assert upload["with"]["retention-days"] == 7
    assert upload["with"]["if-no-files-found"] == "error"


def test_workspace_success_retains_synthetic_scope_and_post_assert_evidence():
    source = (ROOT / "react-app/e2e/workspace/workspace-release.spec.ts").read_text()
    assert "workspace-accessibility.json" in source
    assert "workspace-release-summary.json" in source
    assert "synthetic-api" in source
    assert "post-assert.png" in source
    assert "maxDiffPixelRatio: 0.01" in source
    assert "expect(violations).toEqual([])" in source


def test_browser_diagnostics_are_independent_but_require_successful_setup():
    steps = frontend_steps()
    by_id = {step["id"]: step for step in steps if "id" in step}
    # An explicit status function prevents GitHub's implicit success() from
    # skipping independent diagnostics after an earlier browser assertion fails.
    condition = "always() && steps.scope.outputs.mode == 'full'" + "".join(
        f" && steps.{name}.outcome == 'success'" for name in PREREQUISITES
    )
    for prerequisite in PREREQUISITES:
        assert prerequisite in by_id
        assert "continue-on-error" not in by_id[prerequisite]
    for suite in BROWSER_SUITES.values():
        step = by_id[suite]
        assert " ".join(step["if"].split()) == condition
        assert "continue-on-error" not in step
        assert "|| true" not in step["run"]
        assert max(steps.index(by_id[name]) for name in PREREQUISITES) < steps.index(step)


def test_browser_evidence_attempts_are_distinct_and_uploads_run_after_failure():
    steps = frontend_steps()
    by_id = {step["id"]: step for step in steps if "id" in step}
    attempts = [
        by_id["layout_acceptance"]["env"]["LAYOUT_ATTEMPT"],
        by_id["volcano_acceptance"]["env"]["LAYOUT_ATTEMPT"],
        by_id["journeys_acceptance"]["env"]["JOURNEY_ATTEMPT"],
        by_id["module_journeys_acceptance"]["env"]["JOURNEY_ATTEMPT"],
    ]
    assert len(set(attempts)) == len(attempts)
    assert all(
        "github.run_id" in attempt and "github.run_attempt" in attempt for attempt in attempts
    )
    for name, path in {
        "Upload settings acceptance evidence": ".artifacts/settings-121",
        "Upload user journey evidence": ".artifacts/journeys-*",
        "Upload layout evidence": ".artifacts/layout-109",
    }.items():
        upload = next(step for step in steps if step.get("name") == name)
        assert upload["if"] == "always() && steps.scope.outputs.mode == 'full'"
        assert upload["with"]["path"] == path
        assert upload["with"]["retention-days"] == 7
        assert "continue-on-error" not in upload


def test_browser_aggregate_is_mandatory_and_checks_every_suite():
    steps = frontend_steps()
    gate = next(step for step in steps if step.get("id") == "browser_acceptance")
    assert gate["if"] == "always() && steps.scope.outputs.mode == 'full'"
    assert "continue-on-error" not in gate
    assert gate["env"] == {
        name: "${{ steps." + suite + ".outcome }}" for name, suite in BROWSER_SUITES.items()
    }
    assert steps[-1] is gate


@pytest.mark.parametrize("suite", BROWSER_SUITES)
@pytest.mark.parametrize("outcome", ("failure", "skipped", "cancelled", "", "unknown"))
def test_browser_aggregate_fails_closed_for_each_incomplete_suite(tmp_path, suite, outcome):
    gate = next(step for step in frontend_steps() if step.get("id") == "browser_acceptance")
    summary = tmp_path / "summary.md"
    env = dict(os.environ, GITHUB_STEP_SUMMARY=str(summary))
    env.update(dict.fromkeys(BROWSER_SUITES, "success"))
    env[suite] = outcome
    result = subprocess.run(["bash", "-c", gate["run"]], env=env, capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"::error::{suite} browser acceptance did not pass" in result.stdout
    assert f'| {suite} | {outcome or "missing"} |' in summary.read_text()


def test_browser_aggregate_passes_only_when_all_suites_pass(tmp_path):
    gate = next(step for step in frontend_steps() if step.get("id") == "browser_acceptance")
    summary = tmp_path / "summary.md"
    env = dict(os.environ, GITHUB_STEP_SUMMARY=str(summary))
    env.update(dict.fromkeys(BROWSER_SUITES, "success"))
    result = subprocess.run(["bash", "-c", gate["run"]], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert summary.read_text().count("| success |") == len(BROWSER_SUITES)


def test_loading_evidence_holds_pending_state_until_capture_and_always_releases():
    source = (ROOT / "react-app/e2e/account/settings-platform.spec.ts").read_text()
    loading = source.split("test('loading state retains explicit visual evidence'", 1)[1].split(
        "test('empty-search state retains explicit visual evidence'", 1
    )[0]
    assert "setTimeout" not in loading
    assert "await capabilitiesPending" in loading
    assert loading.count("toHaveAttribute('aria-busy', 'true')") == 2
    assert loading.count("getByText('Loading settings…')).toBeVisible()") == 2
    capture = loading.index("toHaveScreenshot('settings-loading-desktop.png'")
    release = loading.index("releaseCapabilities();")
    assert capture < release
    assert "timeout: 5_000" in loading[capture:release]
    assert "finally {" in loading[capture:release]
    assert "await page.unrouteAll({ behavior: 'wait' })" in loading[release:]
    assert "toHaveAttribute('aria-busy', 'false')" in loading[release:]
    assert "test('partial-error state retains explicit visual evidence'" in source


def test_layout_failures_retain_trace_without_automatic_retry():
    config = (ROOT / 'react-app/playwright.layout.config.mjs').read_text()
    assert "trace: 'retain-on-failure'" in config
    assert 'retries: 0' in config
    workflow = (ROOT / '.github/workflows/ci-frontend.yml').read_text()
    assert 'path: .artifacts/layout-109' in workflow


def test_backend_lint_covers_both_fixed_service_matrix_entries():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci-backend.yml').read_text())
    job = next(job for job in workflow['jobs'].values()
               if job.get('strategy', {}).get('matrix', {}).get('service') == ['api', 'django'])
    lint = next(step for step in job['steps'] if step.get('name') == 'Ruff (lint)')
    assert 'if' not in lint
    assert lint['run'] == 'python -m ruff check "${{ matrix.service }}"'
