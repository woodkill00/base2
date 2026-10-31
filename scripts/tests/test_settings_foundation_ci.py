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
    "MEDIA_HC": "media_hc_acceptance",
    "OPERATIONS_HC": "operations_hc_acceptance",
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
        "Upload user journey evidence": (
            ".artifacts/journeys-ci-${{ github.run_id }}-${{ github.run_attempt }}-journeys\n"
            ".artifacts/journeys-ci-${{ github.run_id }}-${{ github.run_attempt }}-modules\n"
        ),
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


def test_django_lint_tool_is_declared_in_its_own_dev_environment():
    api_pin = next(line for line in (ROOT / 'api/requirements.txt').read_text().splitlines()
                   if line.startswith('ruff=='))
    django_dev = (ROOT / 'requirements-dev-django.txt').read_text().splitlines()
    assert api_pin in django_dev


def test_workspace_authoring_fixture_has_write_permission_and_distinct_public_copy():
    source = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    user = source.split('const fixtureUser = {', 1)[1].split('\n};', 1)[0]
    assert "'content-workspace.write'" in user
    records = source.split('const records = states.map', 1)[1].split('const fixtureUser', 1)[0]
    assert 'publicContent:' in records
    assert 'excerpt: `Curated public ${state} excerpt.`' in records
    assert 'body: `Intentional public ${state} body.`' in records
    assert 'Private synthetic editorial note.' in records
    assert "if (url.pathname.includes('/versions')) return send({ items: [] })" in source
    viewer_test = (ROOT / 'react-app/src/__tests__/content-workspace-public-create.test.jsx').read_text()
    assert "test('viewer cannot open public record creation'" in viewer_test
    assert "auth.user.permissions = ['content-workspace.read']" in viewer_test
    assert "queryByRole('button', { name: 'New record' })).not.toBeInTheDocument()" in viewer_test


def test_workspace_author_capability_is_asserted_before_visual_evidence():
    source = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    start = source.index("await page.goto('/workspace')")
    visible = source.index("await expect(newRecord).toBeVisible()", start)
    enabled = source.index("await expect(newRecord).toBeEnabled()", start)
    assert source.index("getByRole('button', { name: 'New record', exact: true })", start) < visible
    assert visible < enabled < source.index("await page.keyboard.press('Tab')", start)
    assert enabled < source.index('await prepareStableFullPageCapture(page)', start)


def test_related_workspace_browser_fixtures_preserve_public_copy_and_denials():
    review = (ROOT / 'react-app/e2e/layout/workspace-review.spec.ts').read_text()
    journey = (ROOT / 'react-app/e2e/journeys/workspace-journeys.spec.ts').read_text()
    assert "publicContent: { excerpt: 'Public review excerpt', body: 'Public review body' }" in review
    for assertion in ('durable test receipts, not live email', 'never publishes',
                      'This request remains pending', 'expect(writes).toBe(0)'):
        assert assertion in review
    owner = journey.split('const owner = {', 1)[1].split('\n};', 1)[0]
    assert "'content-workspace.write'" in owner
    assert 'publicContent: data.publicContent' in journey
    assert 'expect(data.publicContent).toEqual(publicCopy)' in journey
    assert 'expect(data.publicContent).toEqual(editedPublicCopy)' in journey
    assert 'expect(record.publicContent).toEqual(editedPublicCopy)' in journey
    assert 'permissions: []' in journey and 'expect(workspaceRequests).toBe(0)' in journey
    assert "return route.fulfill({ json: { items: [] } })" in review
    assert "path.endsWith('/versions')" in journey


def test_journey_evidence_uses_exact_current_run_directories_not_hidden_root_glob():
    steps = frontend_steps()
    upload = next(step for step in steps if step.get('name') == 'Upload user journey evidence')
    assert upload['with']['path'].splitlines() == [
        '.artifacts/journeys-ci-${{ github.run_id }}-${{ github.run_attempt }}-journeys',
        '.artifacts/journeys-ci-${{ github.run_id }}-${{ github.run_attempt }}-modules',
    ]
    assert upload['with']['if-no-files-found'] == 'warn'
    assert upload['with'].get('include-hidden-files', False) is False
    assert upload['if'] == "always() && steps.scope.outputs.mode == 'full'"
    for name, suffix in [('Volcano user journey states', 'journeys'),
                         ('Enabled optional module journeys', 'modules')]:
        step = next(item for item in steps if item.get('name') == name)
        assert step['env']['JOURNEY_ATTEMPT'] == 'ci-${{ github.run_id }}-${{ github.run_attempt }}-' + suffix
    config = (ROOT / 'react-app/playwright.journeys.config.mjs').read_text()
    assert 'outputDir: `../.artifacts/journeys-${attempt}`' in config


def test_workspace_divider_asserts_computed_paint_and_real_nonlast_border():
    source = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    helper = source.split('async function assertRecordDivider(', 1)[1].split('\nasync function ', 1)[0]
    assert 'li:not(:last-child)' in helper
    assert 'borderBottomWidth' in helper and 'borderBottomStyle' in helper
    assert "toBe('1px')" in helper and "toBe('solid')" in helper
    assert 'borderBottomColor' in helper
    assert "document.createElement('canvas')" in helper
    assert 'getImageData(0, 0, 1, 1)' in helper
    assert 'toBeGreaterThanOrEqual(254)' in helper
    assert 'toBeGreaterThanOrEqual(25)' in helper
    assert 'toBeLessThanOrEqual(26)' in helper
    assert source.index('await assertRecordDivider(page)') < source.index("await page.keyboard.press('Tab')")


def test_workspace_divider_keeps_forced_color_accessibility_override():
    source = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    helper = source.split('async function assertRecordDivider(', 1)[1].split('async function assertUsable', 1)[0]
    assert "matchMedia('(forced-colors: active)')" in helper
    assert 'if (paint.forcedColors)' in helper
    assert 'color:CanvasText;background-color:Canvas' in helper
    assert 'getComputedStyle(probe)' in helper
    assert 'finally' in helper and 'probe.remove()' in helper
    assert 'expect(paint.color).toEqual(paint.systemText)' in helper
    assert 'not.toEqual(paint.systemCanvas.slice(0, 3))' in helper
    assert 'emulateMedia' not in helper and 'forced-color-adjust' not in helper


def test_workspace_forced_colors_is_a_real_context_option_and_observed_state():
    config = (ROOT / 'react-app/playwright.workspace-release.config.mjs').read_text()
    assert "contextOptions: { forcedColors: 'active' }" in config
    assert "}, { forcedColors: 'active' })" not in config
    source = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    helper = (ROOT / 'react-app/e2e/forced-color-state.ts').read_text()
    assert 'async function assertForcedColorState(' in helper
    assert "matchMedia('(forced-colors: active)').matches" in helper
    assert "matchMedia('(forced-colors: none)').matches" in helper
    assert 'expect(state.active).toBe(expectedActive)' in helper
    assert 'expect(state.none).toBe(!expectedActive)' in helper
    assert source.count('await assertForcedColorState(page, testInfo)') >= 4
    compact = "".join(source.split())
    assert "expect.configure({soft:testInfo.project.name==='chromium-high-contrast',})" in compact
    assert "comparison: testInfo.errors.length === errorsBefore ? 'passed' : 'failed'" in source
    assert "status: failed ? 'failed' : 'passed'" in source
    assert "failed ? 'assertions-completed-with-failures' : 'assertions-completed'" in source
    assert 'maxDiffPixelRatio: 0.01' in source
    assert 'emulateMedia' not in source


def test_all_named_forced_color_configs_use_supported_context_options_without_playwright_import():
    import json
    import subprocess

    # Evaluate only these local config objects with inert Playwright declarations;
    # API-only CI intentionally has no npm browser dependencies installed.
    loader = r"""
const fs = require('node:fs'); const vm = require('node:vm');
const paths = JSON.parse(process.argv[1]); const results = [];
for (const path of paths) {
  let source = fs.readFileSync(path, 'utf8');
  const declaration = "import { defineConfig, devices } from '@playwright/test';";
  if (!source.startsWith(declaration)) throw new Error('Unexpected config imports');
  source = source.slice(declaration.length).replace('export default defineConfig(', 'result = defineConfig(');
  if (/\bimport\s/.test(source)) throw new Error('Unexpected additional import');
  let calls = 0;
  const sandbox = {defineConfig(value) {calls++; return value;}, result: null,
    devices: {'Desktop Chrome': {}, 'Desktop Firefox': {}, 'Desktop Safari': {}, 'iPhone 13': {}}};
  vm.runInNewContext(source, sandbox, {filename: path, timeout: 1000});
  if (calls !== 1) throw new Error('Config declaration missing');
  results.push(sandbox.result.projects);
}
process.stdout.write(JSON.stringify(results));
"""
    names = ('workspace', 'media', 'operations', 'settings')
    paths = [str(ROOT / f'react-app/playwright.{name}-release.config.mjs') for name in names]
    receipt = ROOT / 'specs/106-production-readiness-program/operations-visual-runner.json'
    receipt_before = receipt.read_bytes()
    result = subprocess.run(['node', '-e', loader, json.dumps(paths)], check=True,
                            capture_output=True, text=True, timeout=10)
    assert receipt.read_bytes() == receipt_before  # Config inspection must never execute its reporter.
    matrices = json.loads(result.stdout)
    for name, projects in zip(names, matrices, strict=True):
        active = []
        for project in projects:
            options = project['use']
            assert 'forcedColors' not in options
            forced = options.get('contextOptions', {}).get('forcedColors', 'none')
            if 'high-contrast' in project['name']:
                assert forced == 'active'
                active.append(project['name'])
            else:
                assert forced == 'none'
        assert len(active) == (2 if name == 'settings' else 1)


def test_media_operations_keep_hard_comparisons_and_accepted_receipt_semantics():
    for name in ('media', 'operations'):
        source = (ROOT / f'react-app/e2e/{name}/{name}-release.spec.ts').read_text()
        assert "from '../forced-color-state'" in source
        assert 'test.beforeEach' in source and 'test.afterEach' in source
        assert source.count('await assertForcedColorState(page, testInfo)') >= 4
        assert "emulateMedia({ forcedColors:" not in source
        assert 'expect.soft' not in source and 'expect.configure' not in source
    operations = (ROOT / 'react-app/e2e/operations/operations-release.spec.ts').read_text()
    assert operations.index('await expect(page).toHaveScreenshot(name') < operations.index('const acceptedCapture')
    assert 'body: readFileSync(acceptedCapture)' in operations


def test_forced_color_state_assertion_rejects_wrong_named_media_state():
    import subprocess

    script = r"""
const fs = require('node:fs'); const vm = require('node:vm'); const assert = require('node:assert/strict');
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.split('export async function assertForcedSystemControl', 1)[0];
source = source.replace("import { expect, type Page, type TestInfo, type Locator } from '@playwright/test';", '')
  .replace('export async function', 'async function').replace('page: Page, testInfo: TestInfo', 'page, testInfo');
const sandbox = {expect(value) {return {toBe(expected) {assert.equal(value, expected);}};}};
vm.runInNewContext(source, sandbox, {timeout: 1000});
(async () => {
  for (const name of ['chromium-high-contrast', 'chromium-light', 'firefox-desktop']) {
    const active = name === 'chromium-high-contrast';
    const info = {project: {name}};
    assert.equal(await sandbox.assertForcedColorState({evaluate: async () => ({active, none: !active})}, info), active ? 'active' : 'none');
    await assert.rejects(() => sandbox.assertForcedColorState({evaluate: async () => ({active: !active, none: active})}, info));
    await assert.rejects(() => sandbox.assertForcedColorState({evaluate: async () => ({active, none: active})}, info));
  }
})().catch(error => {process.exitCode = 1; console.error(error);});
"""
    subprocess.run(['node', '-e', script, str(ROOT / 'react-app/e2e/forced-color-state.ts')],
                   check=True, capture_output=True, text=True, timeout=10)


def test_targeted_forced_color_runs_are_partial_diagnostics_not_full_visual_receipts():
    steps = frontend_steps()
    for area in ('media', 'operations'):
        step = next(item for item in steps if item.get('id') == f'{area}_hc_acceptance')
        assert f'npm run test:{area}-release -- --project=chromium-high-contrast --reporter=line' in step['run']
        assert f'--output=../.artifacts/forced-colors-ci-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}-{area}' in step['run']
        assert 'continue-on-error' not in step
    operations = next(item for item in steps if item.get('id') == 'operations_hc_acceptance')
    assert 'sha256sum ../specs/106-production-readiness-program/operations-visual-runner.json' in operations['run']
    assert '|| status=$?' in operations['run'] and 'exit "$status"' in operations['run']
    assert 'git checkout' not in operations['run'] and 'git restore' not in operations['run']
    upload = next(item for item in steps if item.get('name') == 'Retain targeted forced-color diagnostics')
    assert upload['with']['path'].splitlines() == [
        f'.artifacts/forced-colors-ci-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}-{area}'
        for area in ('media', 'operations')]
    assert upload['with'].get('include-hidden-files', False) is False
    assert upload['with']['if-no-files-found'] == 'warn'


@pytest.mark.parametrize('command_status,mutate,expected', [(0, False, 0), (7, False, 7),
                                                          (0, True, 1), (7, True, 7),
                                                          (0, 'remove', 1), (7, 'remove', 7)])
def test_partial_operations_run_preserves_failure_and_never_repairs_receipt(tmp_path, command_status, mutate, expected):
    step = next(item for item in frontend_steps() if item.get('id') == 'operations_hc_acceptance')
    work = tmp_path / 'react-app'
    work.mkdir()
    receipt = tmp_path / 'specs/106-production-readiness-program/operations-visual-runner.json'
    receipt.parent.mkdir(parents=True)
    receipt.write_text('accepted original')
    binary = tmp_path / 'bin'
    binary.mkdir()
    npm = binary / 'npm'
    mutation = f"rm '{receipt}'\n" if mutate == 'remove' else (f"printf changed > '{receipt}'\n" if mutate else '')
    npm.write_text('#!/bin/sh\n' + mutation + f'exit {command_status}\n')
    npm.chmod(0o700)
    command = step['run'].replace('${{ github.run_id }}', '123').replace('${{ github.run_attempt }}', '1')
    result = subprocess.run(['bash', '-c', command], cwd=work,
                            env=dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH']),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == expected
    if mutate == 'remove':
        assert not receipt.exists()
    else:
        assert receipt.read_text() == ('changed' if mutate else 'accepted original')


def test_genuine_hc_controls_assert_system_readability_boundaries_and_selected_cue():
    helper = (ROOT / 'react-app/e2e/forced-color-state.ts').read_text()
    assert 'export async function assertForcedSystemControl' in helper
    assert 'color:ButtonText;background-color:ButtonFace;border:1px solid ButtonText' in helper
    assert 'getImageData(0, 0, 1, 1)' in helper
    assert 'toBeGreaterThanOrEqual(4.5)' in helper
    assert "toBe('1px')" in helper and "toBe('solid')" in helper
    assert 'probe.remove()' in helper
    workspace = (ROOT / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    assert 'assertForcedSystemControl(newRecord)' in workspace
    assert 'textDecorationLine' in workspace and 'textDecorationColor' in workspace
    assert "toContain('underline')" in workspace
    media = (ROOT / 'react-app/e2e/media/media-release.spec.ts').read_text()
    assert "assertForcedSystemControl(picker.getByLabel('Search media', { exact: true }), true)" in media
    assert "assertForcedSystemControl(picker.getByLabel('Status', { exact: true }), true)" in media
    operations = (ROOT / 'react-app/e2e/operations/operations-release.spec.ts').read_text()
    assert 'assertForcedSystemControl(primary)' in operations


def test_partial_operations_hc_selects_only_supported_main_case_not_skipped_states():
    step = next(item for item in frontend_steps() if item.get('id') == 'operations_hc_acceptance')
    assert "--grep='(^| )operations center is accessible responsive and visually stable$'" in step['run']
    source = (ROOT / 'react-app/e2e/operations/operations-release.spec.ts').read_text()
    assert source.count("test('operations center is accessible responsive and visually stable'") == 1
    assert "test('operations center shows truthful empty and failure states'" in source
    assert "test('operations center exposes stale, reauthentication, and read-only recovery states'" in source
