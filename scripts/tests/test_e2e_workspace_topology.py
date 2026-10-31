"""Static boundary contracts; not Docker/browser acceptance."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def stack():
    return yaml.safe_load((ROOT / 'e2e/docker-compose.e2e.yml').read_text())


def test_profile_is_fixed_and_shared_with_real_content_topology():
    services = stack()['services']
    for name in ('api', 'workspace-fixture', 'celery-worker', 'celery-data-rights-worker', 'celery-content-worker', 'celery-beat'):
        assert services[name]['environment']['SITE_PROFILE'] == 'base2-obsidian'
    assert services['react-app']['build']['args']['SITE_PROFILE'] == 'base2-obsidian'
    worker = services['celery-content-worker']
    assert worker['environment']['BASE2_PROCESS_ROLE'] == 'content-worker'
    assert worker['environment']['DB_USER'] == 'base2_workspace_worker_e2e'
    assert '-Q content' in ' '.join(worker['command'])
    assert 'beat' in ' '.join(services['celery-beat']['command'])
    assert services['celery-beat']['environment']['DB_USER'] == 'base2_runtime_worker_e2e'


def test_fixture_is_one_shot_internal_and_artifacts_are_local_encrypted():
    services = stack()['services']
    fixture = services['workspace-fixture']
    assert fixture['environment']['E2E_WORKSPACE_DISPOSABLE'] == '1'
    assert fixture['environment']['DB_USER'] == 'e2e'
    assert fixture['environment']['BASE2_PROCESS_ROLE'] == 'migration'
    assert 'WORKSPACE_WORKER_DB_PASSWORD' not in services['api']['environment']
    assert fixture['command'] == ['python', '/e2e-support/workspace_fixture.py', 'seed']
    assert fixture['depends_on']['django-migrate']['condition'] == 'service_completed_successfully'
    assert services['api']['depends_on']['workspace-fixture']['condition'] == 'service_completed_successfully'
    assert 'ports' not in fixture
    for name in ('api', 'workspace-fixture', 'celery-content-worker'):
        env = services[name]['environment']
        assert env['CONTENT_WORKSPACE_STORAGE_BACKEND'] == 'local'
        assert env['CONTENT_WORKSPACE_STORAGE_KEY']
        assert 'content_workspace_artifacts:/var/lib/base2/content-workspace' in services[name]['volumes']
    assert 'content_workspace_artifacts' in stack()['volumes']
    assert '../e2e/support:/e2e-support:ro' in services['celery-content-worker']['volumes']


def test_supported_runners_and_ci_keep_evidence_on_success_and_failure():
    bash = (ROOT / 'scripts/bash/e2e-isolated-body.sh').read_text()
    ps = (ROOT / 'scripts/powershell/e2e-isolated-body.ps1').read_text()
    for source in (bash, ps):
        assert 'base2-e2e-isolated' in source
        assert 'secure_file_lock.py' in source
        assert 'compose.log' in source
        assert 'PLAYWRIGHT_JSON_OUTPUT_NAME' in source
        assert '--reporter=line,json --workers=1' in source
    workflow = (ROOT / '.github/workflows/ci-e2e.yml').read_text()
    assert 'scripts/bash/e2e-isolated.sh' in workflow
    assert 'if: always()' in workflow
    assert 'e2e/artifacts' in workflow
    assert 'docker compose' not in workflow
    wrapper = (ROOT / 'scripts/powershell/e2e-isolated.ps1').read_text()
    assert 'secure_file_lock.py' in wrapper
    assert 'bash' not in wrapper.lower()


def test_runner_preserves_failed_test_status_and_captures_cleanup(tmp_path, monkeypatch):
    """Fake executables only: never invoke a Docker daemon, npm, or browser."""
    import os
    import shutil
    import subprocess

    root = tmp_path / 'repo'
    for relative in ('scripts/bash/e2e-isolated.sh', 'scripts/bash/e2e-isolated-body.sh', 'scripts/python/secure_file_lock.py'):
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    (root / 'e2e').mkdir()
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    scripts = {
        'docker': '#!/bin/sh\nprintf "synthetic compose %s\\n" "$*"\nexit 0\n',
        'curl': '#!/bin/sh\nexit 0\n',
        'git': '#!/bin/sh\nprintf "synthetic-source\\n"\n',
        'npm': '#!/bin/sh\nprintf "{\\"synthetic\\":true}\\n" > "$PLAYWRIGHT_JSON_OUTPUT_NAME"\nexit 7\n',
    }
    for name, script in scripts.items():
        executable = binaries / name
        executable.write_text(script)
        executable.chmod(0o700)
    monkeypatch.setenv('PATH', str(binaries) + os.pathsep + os.environ['PATH'])
    result = subprocess.run(['bash', str(root / 'scripts/bash/e2e-isolated.sh')], capture_output=True, text=True, timeout=10)
    assert result.returncode == 7, result.stderr
    evidence = root / 'e2e/artifacts'
    assert (evidence / 'exit-code.txt').read_text().strip() == '7'
    assert 'down -v --remove-orphans' in (evidence / 'cleanup.log').read_text()
    assert 'logs --no-color' in (evidence / 'compose.log').read_text()
    assert (evidence / 'playwright.json').is_file()


def test_ci_exercises_both_shells_in_separate_jobs_without_failure_cancellation():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci-e2e.yml').read_text())
    job = workflow['jobs']['e2e']
    assert job['runs-on'] == 'ubuntu-latest'
    assert job['strategy']['fail-fast'] is False
    assert job['strategy']['matrix']['runner-shell'] == ['bash', 'pwsh']
    steps = job['steps']
    for shell, command in (
        ('bash', 'bash scripts/bash/e2e-isolated.sh'),
        ('pwsh', './scripts/powershell/e2e-isolated.ps1'),
    ):
        step = next(step for step in steps if step.get('shell') == shell and step.get('run') == command)
        assert step['if'] == f"matrix.runner-shell == '{shell}'"
    artifact = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    assert artifact['if'] == 'always()'
    assert artifact['with']['name'] == 'e2e-real-service-evidence-${{ matrix.runner-shell }}'


def test_fixture_and_journey_contracts_are_collected_in_api_ci_and_complete_gate():
    import json
    import shlex

    paths = (
        'scripts/tests/test_e2e_workspace_topology.py',
        'e2e/support/test_workspace_fixture.py',
        'e2e/support/test_workspace_journey_source.py',
    )
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci-backend.yml').read_text())
    steps = next(job['steps'] for job in workflow['jobs'].values()
                 if job.get('strategy', {}).get('matrix', {}).get('service') == ['api', 'django'])
    regression = next(step for step in steps
                      if 'scripts/tests/test_frontend_ci_scope.py' in step.get('run', ''))
    assert regression['if'] == "matrix.service == 'api'"
    command = shlex.split(regression['run'])
    assert command[:4] == ['python', '-m', 'pytest', '-q']
    assert all(path in command for path in paths)
    node = next(step for step in steps if step.get('uses', '').startswith('actions/setup-node@'))
    assert node['if'] == "matrix.service == 'api'"
    assert node['uses'] == 'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020'
    assert node['with']['node-version'] == '20'
    assert steps.index(node) < steps.index(regression)
    manifest = json.loads((ROOT / 'scripts/config/complete-gate-v1.json').read_text())
    gate = next(check for check in manifest['checks'] if check['id'] == 'frontend-ci-scope-contract')
    assert gate['command'][:4] == ['{python-api}', '-m', 'pytest', '-q']
    assert all(path in gate['command'] for path in paths)
    assert {'{python-api}', 'node'} <= set(gate['requiredTools'])
    assert gate['required'] is True


def test_runtime_worker_mounts_only_canonical_read_only_operations_catalog():
    import json

    source = '../shared/config/operations-probes-v1.json'
    target = '/app/shared/config/operations-probes-v1.json'
    mounts = stack()['services']['celery-worker'].get('volumes', [])
    assert mounts == [f'{source}:{target}:ro']
    canonical = (ROOT / 'e2e' / source).resolve()
    assert canonical == ROOT / 'shared/config/operations-probes-v1.json'
    catalog = json.loads(canonical.read_text())
    assert catalog['schemaVersion'] == 1
    probes = catalog['probes']
    assert isinstance(probes, list) and probes
    assert len({probe['id'] for probe in probes}) == len(probes)
    for probe in probes:
        assert isinstance(probe['id'], str) and probe['id']
        assert isinstance(probe['kind'], str) and probe['kind']
        assert isinstance(probe['freshnessSeconds'], int) and probe['freshnessSeconds'] > 0
        assert isinstance(probe['timeoutSeconds'], int) and probe['timeoutSeconds'] > 0
    development = yaml.safe_load((ROOT / 'development.docker.yml').read_text())
    assert f'./shared/config/operations-probes-v1.json:{target}:ro' in development['services']['celery-worker']['volumes']
