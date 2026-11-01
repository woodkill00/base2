"""Opt-in native visual evidence stays exact-source and never approves itself."""
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / '.github/workflows/ci-visual-review.yml'
RECEIPT = 'specs/106-production-readiness-program/operations-visual-runner.json'


def workflow():
    return yaml.safe_load(PATH.read_text())


def steps():
    return {step['id']: step for step in workflow()['jobs']['visual-review']['steps'] if 'id' in step}


def test_opt_in_is_closed_same_repository_exact_head_read_only():
    data = workflow()
    assert data.get('on', data.get(True)) == {'pull_request': {'types': ['labeled']}}
    assert data['permissions'] == {'contents': 'read'}
    assert data['concurrency']['cancel-in-progress'] is False
    job = data['jobs']['visual-review']
    assert job['if'] == "github.event.pull_request.head.repo.full_name == github.repository && (github.event.label.name == 'run-operations-review' || github.event.label.name == 'run-media-review')"
    assert job['timeout-minutes'] == 90
    assert job['steps'][0]['with'] == {'ref': '${{ github.event.pull_request.head.sha }}', 'fetch-depth': 0, 'persist-credentials': False}
    for forbidden in ['pull_request_target', 'secrets.', 'continue-on-error', '|| true', 'git reset', 'git restore', 'docker ', 'workflow_dispatch']:
        assert forbidden not in PATH.read_text()
    for step in job['steps']:
        if 'uses' in step:
            assert len(step['uses'].rsplit('@', 1)[1]) == 40


def test_full_matrices_keep_reporter_and_baselines_unchanged():
    run = steps()['matrix']['run']
    assert 'npm run test:operations-release -- --update-snapshots=none' in run
    assert '--reporter=line,json,./e2e/operations/visual-receipt-reporter.mjs' in run
    assert 'npm run test:media-release -- --update-snapshots=none --reporter=line,json' in run
    for flag in ['--project', '--grep', '--retries', '--max-failures']:
        assert flag not in run
    assert '*) exit 2 ;;' in run
    ordered = list(steps())
    assert ordered.index('fonts') < ordered.index('before') < ordered.index('matrix') < ordered.index('after')
    assert 'npm ci --prefix react-app --legacy-peer-deps' in steps()['install']['run']
    assert 'chromium firefox webkit' in steps()['browsers']['run']
    assert 'fonts-ubuntu=0.869+git20240321-0ubuntu1' in steps()['fonts']['run']


def test_artifacts_only_include_owned_review_outputs():
    upload = steps()['evidence']
    assert upload['if'] == 'always()'
    assert upload['with']['retention-days'] == 7
    assert upload['with']['path'].splitlines() == [
        '${{ env.VISUAL_OUTPUT }}/test-results/',
        '${{ env.VISUAL_OUTPUT }}/playwright.json',
        '${{ env.VISUAL_OUTPUT }}/source-before.json',
        '${{ env.VISUAL_OUTPUT }}/source-after.json',
        '${{ env.VISUAL_OUTPUT }}/operations-visual-runner.json',
        '${{ env.VISUAL_OUTPUT }}/stages.md',
    ]
    assert 'operations-visual-review.json' not in PATH.read_text()


def python_body(step_id):
    return steps()[step_id]['run'].split("<<'PYTHON'\n", 1)[1].rsplit('\nPYTHON', 1)[0]


def test_workflow_inline_sources_and_shell_parse_without_execution():
    for step in steps().values():
        if 'run' not in step:
            continue
        subprocess.run(['bash', '-n'], input=step['run'], text=True, check=True, timeout=10)
        if "<<'PYTHON'" in step['run']:
            ast.parse(python_body(step['id']))


def native_failed_reporter_fixture(root):
    """Exercise real reporter code with a failed unit fixture, never a pass receipt."""
    (root / 'react-app').mkdir(exist_ok=True)
    subprocess.run(
        [shutil.which('node'), '--input-type=module', '-e',
         "const {default: Reporter} = await import(process.env.REPORTER_URI); new Reporter().onEnd({status: 'failed'});"],
        cwd=root / 'react-app', timeout=10, check=True, capture_output=True, text=True,
        env={'PATH': '/usr/bin:/bin', 'REPORTER_URI': (ROOT / 'react-app/e2e/operations/visual-receipt-reporter.mjs').as_uri()},
    )


def fixture_repository(root):
    environment = {'PATH': os.environ['PATH'], 'HOME': str(root),
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}

    def git(*args):
        return subprocess.run(['git', *args], cwd=root, env=environment,
                              text=True, capture_output=True, check=True, timeout=10).stdout.strip()

    git('init', '-q')
    (root / '.gitignore').write_text('.artifacts/\n')
    (root / 'baseline.png').write_bytes(b'unit baseline, not an image')
    native_failed_reporter_fixture(root)
    for mode in ['operations', 'media']:
        for name in [f'react-app/playwright.{mode}-release.config.mjs',
                     f'react-app/e2e/{mode}/{mode}-release.spec.ts']:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
    git('add', '.')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
        'commit', '-qm', 'isolated review fixture')
    environment.update(EXPECTED_SHA=git('rev-parse', 'HEAD'), REVIEW_LABEL='run-operations-review',
                       VISUAL_OUTPUT='.artifacts/visual-matrix/11-1', GITHUB_RUN_ID='11', GITHUB_RUN_ATTEMPT='1')
    return git, environment


def run_python_step(step_id, root, environment):
    return subprocess.run([sys.executable, '-'], input=python_body(step_id), cwd=root,
                          env=environment, text=True, capture_output=True, timeout=15, check=False)


def test_operations_actual_failed_reporter_output_is_only_allowed_tracked_change(tmp_path):
    _, environment = fixture_repository(tmp_path)
    original = (tmp_path / RECEIPT).read_bytes()
    before = run_python_step('before', tmp_path, environment)
    assert before.returncode == 0, before.stderr
    assert not (tmp_path / RECEIPT).exists()
    native_failed_reporter_fixture(tmp_path)
    after = run_python_step('after', tmp_path, {**environment, 'MATRIX_OUTCOME': 'failure'})
    assert after.returncode == 0, after.stderr
    output = tmp_path / environment['VISUAL_OUTPUT']
    assert (output / 'operations-visual-runner.json').read_bytes() == (tmp_path / RECEIPT).read_bytes() == original
    metadata = json.loads((output / 'source-after.json').read_text())
    assert metadata['nativeOutcome'] == 'failure'
    assert metadata['freshOperationsReceipt'] is True
    assert metadata['declaredTests'] == 0  # Never promoted into full-matrix evidence.


def test_unchanged_old_receipt_cannot_be_used_as_success(tmp_path):
    _, environment = fixture_repository(tmp_path)
    assert run_python_step('before', tmp_path, environment).returncode == 0
    result = run_python_step('after', tmp_path, {**environment, 'MATRIX_OUTCOME': 'success'})
    assert result.returncode != 0
    assert 'successful_operations_missing_fresh_reporter' in result.stderr
    assert 'successful_matrix_missing_full_inventory' in result.stderr
    assert not (tmp_path / environment['VISUAL_OUTPUT'] / 'operations-visual-runner.json').exists()


def test_operations_output_exception_does_not_hide_baseline_drift(tmp_path):
    _, environment = fixture_repository(tmp_path)
    assert run_python_step('before', tmp_path, environment).returncode == 0
    (tmp_path / 'baseline.png').write_bytes(b'changed unit baseline')
    result = run_python_step('after', tmp_path, {**environment, 'MATRIX_OUTCOME': 'failure'})
    assert result.returncode != 0
    assert 'visual_inputs_or_baselines_changed' in result.stderr
    assert (tmp_path / 'baseline.png').read_bytes() == b'changed unit baseline'  # No reset.


def test_media_has_no_reporter_output_exception(tmp_path):
    _, environment = fixture_repository(tmp_path)
    environment['REVIEW_LABEL'] = 'run-media-review'
    assert run_python_step('before', tmp_path, environment).returncode == 0
    (tmp_path / RECEIPT).write_text('changed reporter output')
    result = run_python_step('after', tmp_path, {**environment, 'MATRIX_OUTCOME': 'failure'})
    assert result.returncode != 0
    assert 'visual_inputs_or_baselines_changed' in result.stderr
    assert not (tmp_path / environment['VISUAL_OUTPUT'] / 'operations-visual-runner.json').exists()


def test_pre_run_rejects_dirty_source(tmp_path):
    _, environment = fixture_repository(tmp_path)
    (tmp_path / 'unexpected.txt').write_text('untracked source')
    result = run_python_step('before', tmp_path, environment)
    assert result.returncode != 0
    assert 'visual_source_not_clean_or_exact' in result.stderr


def test_declared_supported_and_skip_counts_come_from_current_specs(tmp_path):
    _, environment = fixture_repository(tmp_path)
    assert run_python_step('before', tmp_path, environment).returncode == 0
    before = json.loads((tmp_path / environment['VISUAL_OUTPUT'] / 'source-before.json').read_text())
    assert len(before['expectedTests']) == 42
    assert sum(item['expectedStatus'] == 'passed' for item in before['expectedTests']) == 22
    media = tmp_path / 'separate-media-checkout'
    media.mkdir()
    _, environment = fixture_repository(media)
    environment.update(REVIEW_LABEL='run-media-review', VISUAL_OUTPUT='.artifacts/visual-matrix/12-1')
    assert run_python_step('before', media, environment).returncode == 0
    before = json.loads((media / environment['VISUAL_OUTPUT'] / 'source-before.json').read_text())
    assert len(before['expectedTests']) == 36
    assert sum(item['expectedStatus'] == 'passed' for item in before['expectedTests']) == 24


def test_all_skipped_full_inventory_cannot_be_accepted_as_execution(tmp_path):
    _, environment = fixture_repository(tmp_path)
    environment['REVIEW_LABEL'] = 'run-media-review'
    assert run_python_step('before', tmp_path, environment).returncode == 0
    output = tmp_path / environment['VISUAL_OUTPUT']
    before = json.loads((output / 'source-before.json').read_text())
    # Intentionally invalid all-skipped fixture, never an accepted run receipt.
    payload = {'suites': [{'specs': [
        {'title': item['title'], 'tests': [{'projectName': item['project'], 'status': 'skipped',
                                          'results': [{'status': 'skipped'}]}]}
        for item in before['expectedTests']
    ]}]}
    (output / 'playwright.json').write_text(json.dumps(payload))
    result = run_python_step('after', tmp_path, {**environment, 'MATRIX_OUTCOME': 'success'})
    assert result.returncode != 0
    assert 'successful_matrix_zero_supported_execution' in result.stderr
    assert 'successful_matrix_supported_or_skip_status_mismatch' in result.stderr
    assert 'successful_matrix_missing_full_inventory' not in result.stderr


def test_workflow_never_evaluates_source_in_process():
    for step_id in ['before', 'after']:
        tree = ast.parse(python_body(step_id))
        assert not [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id in {'exec', 'eval'}]


def test_direct_contract_is_executed_by_standard_api_ci():
    backend = yaml.safe_load((ROOT / '.github/workflows/ci-backend.yml').read_text())
    step = next(step for step in backend['jobs']['backend']['steps'] if step.get('name') == 'Frontend/E2E acceptance contracts')
    assert 'scripts/tests/test_visual_matrix_ci.py' in step['run']
    assert step['if'] == "matrix.service == 'api'"


def test_nominal_supported_inventory_without_actual_captures_is_rejected(tmp_path):
    _, environment = fixture_repository(tmp_path)
    environment['REVIEW_LABEL'] = 'run-media-review'
    assert run_python_step('before', tmp_path, environment).returncode == 0
    output = tmp_path / environment['VISUAL_OUTPUT']
    before = json.loads((output / 'source-before.json').read_text())
    # Deliberately invalid nominal-success JSON fixture: no current screenshots.
    # It must fail, and is never emitted as native/accepted evidence.
    payload = {'suites': [{'specs': [
        {'title': item['title'], 'tests': [{'projectName': item['project'],
            'status': 'expected' if item['expectedStatus'] == 'passed' else 'skipped',
            'results': [{'status': item['expectedStatus']}]}]}
        for item in before['expectedTests']
    ]}]}
    (output / 'playwright.json').write_text(json.dumps(payload))
    result = run_python_step('after', tmp_path, {**environment, 'MATRIX_OUTCOME': 'success'})
    assert result.returncode != 0
    assert result.stderr.strip() == 'successful_matrix_missing_current_captures'


def test_unknown_label_rejected_before_output_preparation(tmp_path):
    _, environment = fixture_repository(tmp_path)
    environment['REVIEW_LABEL'] = 'run-something-else'
    original = (tmp_path / RECEIPT).read_bytes()
    result = run_python_step('before', tmp_path, environment)
    assert result.returncode != 0
    assert (tmp_path / RECEIPT).read_bytes() == original
    assert not (tmp_path / environment['VISUAL_OUTPUT']).exists()
