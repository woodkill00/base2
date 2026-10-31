"""Source contracts for opt-in exact-head hosted complete-gate execution."""
import ast
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / '.github/workflows/ci-complete-gate.yml'


def workflow():
    return yaml.safe_load(PATH.read_text())


def test_admission_is_same_repository_explicit_label_event_only():
    data = workflow()
    events = data.get('on', data.get(True))
    assert events == {'pull_request': {'types': ['labeled']}}
    job = data['jobs']['complete-gate']
    assert job['if'] == (
        "github.event.label.name == 'run-complete-gate' && "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    assert data['permissions'] == {'contents': 'read'}
    assert data['concurrency']['cancel-in-progress'] is False
    assert job['timeout-minutes'] == 360
    assert job['runs-on'] == 'ubuntu-24.04'
    assert job['defaults']['run']['shell'] == 'bash'


def test_checkout_is_exact_head_full_history_without_credentials():
    steps = workflow()['jobs']['complete-gate']['steps']
    checkout = steps[0]
    assert checkout['with'] == {
        'ref': '${{ github.event.pull_request.head.sha }}',
        'fetch-depth': 0,
        'persist-credentials': False,
    }
    binding = next(step for step in steps if step.get('id') == 'source')
    assert binding['env']['EXPECTED_SHA'] == '${{ github.event.pull_request.head.sha }}'
    assert 'git rev-parse HEAD' in binding['run']
    assert 'git status --porcelain=v1 --untracked-files=all' in binding['run']


def test_prerequisites_and_repetitions_precede_unchanged_supported_gate():
    steps = workflow()['jobs']['complete-gate']['steps']
    ids = [step.get('id') for step in steps]
    required = ['source', 'python', 'node', 'dependencies', 'browsers', 'fonts', 'images', 'clean', 'repetitions', 'gate', 'evidence']
    assert [item for item in ids if item in required] == required
    by_id = {step['id']: step for step in steps if 'id' in step}
    deps = by_id['dependencies']['run']
    for name in ['requirements-dev-api.txt', 'requirements-dev-django.txt', 'digital_ocean/requirements.txt']:
        assert name in deps
    assert '-r requirements-dev.txt' not in deps  # conflicting pytest-cov pins
    assert deps.count('-m pip check') == 3
    assert 'npm ci --prefix react-app --legacy-peer-deps' in deps
    assert 'npm ci --prefix e2e' in deps
    assert 'chromium firefox webkit' in by_id['browsers']['run']
    assert 'npm --prefix e2e run install:browsers' in by_id['browsers']['run']
    assert 'fonts-ubuntu=0.869+git20240321-0ubuntu1' in by_id['fonts']['run']
    images = by_id['images']['run']
    for service in ['api', 'django']:
        assert f'--tag base2-local-{service}:latest {service}' in images
    assert by_id['repetitions']['run'] == '.venv/bin/python digital_ocean/scripts/python/feature_106_repetitions.py'
    assert by_id['gate']['run'] == 'bash scripts/bash/complete-gate.sh'
    assert 'if' not in by_id['gate']
    assert 'git status --porcelain=v1 --untracked-files=all' in by_id['clean']['run']


def test_evidence_is_narrow_failure_preserving_and_no_privileged_inputs():
    data = workflow()
    steps = data['jobs']['complete-gate']['steps']
    text = PATH.read_text()
    for forbidden in ['pull_request_target', 'secrets.', 'continue-on-error', '|| true', '--update-snapshots', 'workflow_dispatch', 'docker system prune']:
        assert forbidden not in text
    for step in steps:
        if 'uses' in step:
            assert len(step['uses'].rsplit('@', 1)[1]) == 40
    evidence = next(step for step in steps if step.get('id') == 'evidence')
    assert evidence['if'] == 'always()'
    assert evidence['with']['if-no-files-found'] == 'error' 
    assert evidence['with']['retention-days'] == 7
    paths = evidence['with']['path'].splitlines()
    assert paths == [
        '${{ runner.temp }}/complete-gate-evidence/stages.md',
        '${{ runner.temp }}/complete-gate-evidence/receipts.tar',
    ]



def test_supplemental_dependencies_honor_existing_pins_and_import_preflight():
    steps = workflow()['jobs']['complete-gate']['steps']
    deps = next(step['run'] for step in steps if step.get('id') == 'dependencies')
    for pin, source in [
        ('jsonschema==4.25.1', 'digital_ocean/requirements.txt'),
        ('cryptography==50.0.1', 'api/requirements.txt'),
        ('psycopg2-binary==2.9.12', 'api/requirements.txt'),
    ]:
        assert pin in (ROOT / source).read_text().splitlines()
        assert pin in deps
    assert '"$GITHUB_WORKSPACE/.venv-api/bin" >> "$GITHUB_PATH"' in deps
    for prefix, modules in [
        ('.venv/bin/python', ['azure.core.exceptions', 'cryptography', 'jsonschema', 'psycopg2', 'pydo']),
        ('.venv-api/bin/python', ['celery', 'fastapi', 'pypdf', 'pydantic_settings', 'redis', 'jsonschema']),
        ('.venv-django/bin/python', ['django', 'pytest_django', 'mypy', 'ruff']),
    ]:
        preflight = next(line for line in deps.splitlines() if line.startswith(prefix + " -c 'import "))
        assert all(module in preflight for module in modules)
    assert 'test "$(node --version)" = v24.20.0' in deps
    assert 'test "$(npm --version)" = 11.19.0' in deps


def test_setup_failure_summary_reports_only_fixed_step_outcomes():
    summary = next(step for step in workflow()['jobs']['complete-gate']['steps'] if step['name'].startswith('Summarize'))
    assert summary['if'] == 'always()'
    assert all(value.startswith('${{ steps.') and value.endswith('.outcome }}') for value in summary['env'].values())
    assert 'Setup failure or skipped gate is not a complete-gate pass.' in summary['run']
    assert 'env' not in summary['run']
    assert 'printenv' not in PATH.read_text()


def test_archiving_is_allowlisted_private_and_validated_before_upload():
    steps = workflow()['jobs']['complete-gate']['steps']
    package = next(step for step in steps if step.get('id') == 'package')
    assert package['if'] == "always() && steps.source.outcome == 'success'"
    script = package['run']
    for guard in ['member.is_symlink()', 'metadata.st_uid != os.getuid()',
                  'stat.S_IMODE(metadata.st_mode) != expected_mode',
                  'metadata.st_nlink != 1', 'member.resolve().is_relative_to(root)',
                  'recursive=False', "archive.open('xb')", 'bundle.getmembers()',
                  'validate_gate_evidence(result, root)', '_validate_existing(repetitions,',
                  'successful_gate_missing_receipt', 'gate_source_mismatch',
                  'successful_gate_receipt_invalid']:
        assert guard in script
    assert "'.artifacts/complete-gate/*/result.json'" in script
    assert "'.artifacts/feature-106-repetitions/failures/*/*/failure.log'" in script
    assert "'.env'" not in script
    assert 'compose.log' not in script
    compile(script.split("<<'PYTHON'\n", 1)[1].rsplit('\nPYTHON', 1)[0], '<archive>', 'exec')


def archive_code():
    step = next(step for step in workflow()['jobs']['complete-gate']['steps'] if step.get('id') == 'package')
    return step['run'].split("<<'PYTHON'\n", 1)[1].rsplit('\nPYTHON', 1)[0]


def run_archive(root, *, gate_outcome='skipped', repetitions_outcome='skipped', source_sha='a' * 40):
    # Execute the actual trusted workflow body in a child, never in the test
    # interpreter. Only fixed imports and synthetic stage metadata are inherited.
    return subprocess.run(
        [sys.executable, '-'],
        input=archive_code(),
        cwd=root,
        env={
            'HOME': str(root),
            'PATH': '/usr/bin:/bin',
            'LANG': 'C.UTF-8',
            'PYTHONPATH': str(ROOT),
            'PYTHONDONTWRITEBYTECODE': '1',
            'GATE_OUTCOME': gate_outcome,
            'REPETITIONS_OUTCOME': repetitions_outcome,
            'EXPECTED_SHA': source_sha,
            'RUNNER_TEMP': str(root / 'runner-temp'),
        },
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_success_without_receipt_fails_closed(tmp_path):
    result = run_archive(tmp_path, gate_outcome='success')
    assert result.returncode != 0
    assert result.stderr.strip() == 'successful_gate_missing_receipt'


def test_setup_failure_needs_no_fabricated_receipts(tmp_path):
    result = run_archive(tmp_path)
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.rglob('*.tar'))


def test_archive_rejects_symlink_without_reading_target(tmp_path):
    target = tmp_path / 'do-not-read'
    target.write_text('not evidence')
    root = tmp_path / '.artifacts/complete-gate/run'
    root.mkdir(parents=True)
    (root / 'result.json').symlink_to(target)
    result = run_archive(tmp_path)
    assert result.returncode != 0
    assert result.stderr.strip() == 'unsafe_evidence_member'
    assert target.read_text() == 'not evidence'


def test_failed_runner_receipt_archive_preserves_modes_and_exact_members(tmp_path):
    from scripts.python.run_complete_gate import run_gate

    sha = 'a' * 40
    result = run_gate({'schemaVersion': 1, 'checks': [{
        'id': 'intentional-failure', 'command': [sys.executable, '-c', 'raise SystemExit(1)'],
        'required': True, 'timeoutSeconds': 10, 'dependsOn': [], 'requiredTools': [],
    }]}, tmp_path, tmp_path / '.artifacts/complete-gate/unit-fixture', source_commit=sha)
    assert result['overallStatus'] == 'failed'
    runner_temp = tmp_path / 'runner-temp'
    (runner_temp / 'complete-gate-evidence').mkdir(parents=True)
    archived = run_archive(tmp_path, gate_outcome='failure', source_sha=sha)
    assert archived.returncode == 0, archived.stderr
    with tarfile.open(runner_temp / 'complete-gate-evidence/receipts.tar') as bundle:
        members = bundle.getmembers()
    assert {member.name for member in members if member.isfile()} == {
        '.artifacts/complete-gate/unit-fixture/result.json',
        '.artifacts/complete-gate/unit-fixture/intentional-failure.log',
    }
    assert all(member.mode == (0o700 if member.isdir() else 0o600) for member in members)
    assert not (runner_temp / 'complete-gate-evidence/receipts.tar.pending').exists()


def test_archive_harness_does_not_evaluate_source_in_process():
    tree = ast.parse(Path(__file__).read_text())
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id in {'exec', 'eval'}]


def test_archive_child_has_fixed_argv_bounded_timeout_and_no_ambient_credentials(tmp_path, monkeypatch):
    captured = {}

    def capture(command, **kwargs):
        captured.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 17, '', 'original failure')

    monkeypatch.setenv('UNRELATED_SECRET', 'must-not-inherit')
    monkeypatch.setattr(subprocess, 'run', capture)
    result = run_archive(tmp_path)
    assert captured['command'] == [sys.executable, '-']
    assert captured['input'] == archive_code()
    assert captured['cwd'] == tmp_path
    assert captured['timeout'] == 10
    assert captured['check'] is False
    assert captured['capture_output'] is True
    assert 'shell' not in captured
    assert 'UNRELATED_SECRET' not in captured['env']
    assert captured['env']['PYTHONPATH'] == str(ROOT)
    assert result.returncode == 17 and result.stderr == 'original failure'


def test_archive_child_timeout_is_not_swallowed(tmp_path, monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])

    monkeypatch.setattr(subprocess, 'run', timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        run_archive(tmp_path)


def test_root_install_matches_existing_locked_security_peer_policy():
    security = yaml.safe_load((ROOT / '.github/workflows/security.yml').read_text())
    root_audit = next(step['run'] for step in security['jobs']['npm-audit']['steps']
                      if step.get('name') == 'Install root deps')
    root_licenses = next(step['run'].splitlines()[0] for step in security['jobs']['node-licenses']['steps']
                         if step.get('name') == 'Install locked Node dependencies')
    dependencies = next(step['run'] for step in workflow()['jobs']['complete-gate']['steps']
                        if step.get('id') == 'dependencies')
    root_install = [line for line in dependencies.splitlines()
                    if line.startswith('npm ci') and '--prefix' not in line]
    assert root_install == [root_audit] == [root_licenses] == ['npm ci --legacy-peer-deps']


def fresh_source_repository(root):
    environment = {'PATH': '/usr/bin:/bin', 'HOME': str(root),
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}

    def git(*args):
        return subprocess.run(['git', *args], cwd=root, env=environment,
                              text=True, capture_output=True, timeout=10, check=True).stdout.strip()

    git('init', '-q')
    (root / '.gitignore').write_text((ROOT / '.gitignore').read_text())
    (root / 'source.txt').write_text('original source\n')
    git('add', '.gitignore', 'source.txt')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
        'commit', '-qm', 'isolated source fixture')
    return git, environment


def run_source_guard(root, sha, environment):
    clean = next(step['run'] for step in workflow()['jobs']['complete-gate']['steps']
                 if step.get('id') == 'clean')
    guard = clean.split('.venv-api/bin/python -m pytest', 1)[0]
    return subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', guard], cwd=root,
                          env={**environment, 'EXPECTED_SHA': sha}, text=True,
                          capture_output=True, timeout=10, check=False)


def test_fresh_checkout_generated_environments_do_not_dirty_source(tmp_path):
    git, environment = fresh_source_repository(tmp_path)
    sha = git('rev-parse', 'HEAD')
    for name in ['.venv', '.venv-api', '.venv-django']:
        (tmp_path / name).mkdir()
        (tmp_path / name / 'pyvenv.cfg').write_text('synthetic generated environment\n')
    assert git('status', '--porcelain=v1', '--untracked-files=all') == ''
    assert run_source_guard(tmp_path, sha, environment).returncode == 0


@pytest.mark.parametrize('change', ['tracked', 'untracked', 'nested-environment'])
def test_generated_ignores_do_not_hide_other_source_changes(tmp_path, change):
    git, environment = fresh_source_repository(tmp_path)
    sha = git('rev-parse', 'HEAD')
    paths = {'tracked': 'source.txt', 'untracked': 'other.txt',
             'nested-environment': 'nested/.venv-api/source.py'}
    path = tmp_path / paths[change]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('changed source\n')
    result = run_source_guard(tmp_path, sha, environment)
    assert result.returncode != 0
    assert 'dirty-source:' in result.stdout
    assert paths[change] in result.stdout


def test_dirty_source_diagnostics_are_quoted_bounded_paths_only(tmp_path):
    git, environment = fresh_source_repository(tmp_path)
    sha = git('rev-parse', 'HEAD')
    for number in range(30):
        name = f'{number:02d}-::warning::\n' + 'x' * 180
        (tmp_path / name).write_text('NEVER_EMIT_FILE_CONTENTS')
    result = run_source_guard(tmp_path, sha, environment)
    assert result.returncode != 0
    lines = result.stdout.splitlines()
    assert lines[0] == 'dirty-source-count: 30'
    assert len(lines) == 21
    assert all(line.startswith("dirty-source: '") for line in lines[1:])
    assert all(len(line) <= 1000 for line in lines)
    assert 'NEVER_EMIT_FILE_CONTENTS' not in result.stdout


def test_generated_ignore_does_not_hide_changes_to_already_tracked_file(tmp_path):
    git, environment = fresh_source_repository(tmp_path)
    path = tmp_path / '.venv-api/tracked.txt'
    path.parent.mkdir()
    path.write_text('tracked original')
    git('add', '-f', '.venv-api/tracked.txt')
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
        'commit', '-qm', 'tracked-file negative fixture')
    sha = git('rev-parse', 'HEAD')
    path.write_text('changed tracked source')
    result = run_source_guard(tmp_path, sha, environment)
    assert result.returncode != 0
    assert '.venv-api/tracked.txt' in result.stdout


def test_clean_guard_still_rejects_different_source_sha(tmp_path):
    _, environment = fresh_source_repository(tmp_path)
    result = run_source_guard(tmp_path, '0' * 40, environment)
    assert result.returncode != 0
