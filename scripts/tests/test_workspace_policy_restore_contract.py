"""The restoration proof may only target two exact-owned disposable databases."""
import subprocess

import pytest

from scripts.python import workspace_policy_restore_fixture as fixture


def test_restore_requires_both_disposable_guards(monkeypatch):
    monkeypatch.delenv('WORKSPACE_POLICY_DISPOSABLE', raising=False)
    monkeypatch.delenv('WORKSPACE_RESTORE_DISPOSABLE', raising=False)
    with pytest.raises(fixture.RestoreFixtureError, match='disposable_required'):
        fixture.require_disposable()
    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    with pytest.raises(fixture.RestoreFixtureError, match='disposable_required'):
        fixture.require_disposable()
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '1')
    fixture.require_disposable()


def test_names_are_unique_distinct_and_never_accept_caller_target():
    first, second = fixture.database_names(), fixture.database_names()
    assert len(set(first + second)) == 4
    assert first[0].startswith('base2_test_policy_')
    assert first[1].startswith('base2_restore_policy_')
    assert all(len(name) < 64 for name in first + second)


@pytest.mark.parametrize('version', ['psql (PostgreSQL) 15.9', 'unknown', 'pg_dump (PostgreSQL) 17.0'])
def test_tool_major_mismatch_fails_before_database_creation(version):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, version, '')
    with pytest.raises(fixture.RestoreFixtureError, match='postgres_client_version'):
        fixture.verify_clients(160004, runner=run, which=lambda _: '/tool')


def test_missing_tool_is_blocked_not_skipped():
    with pytest.raises(fixture.RestoreFixtureError, match='postgres_client_missing'):
        fixture.verify_clients(160004, which=lambda _: None)


def test_matching_tools_are_all_checked_with_bounded_execution():
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, f'{command[0]} (PostgreSQL) 16.4', '')
    fixture.verify_clients(160004, runner=run, which=lambda name: '/bin/' + name)
    assert [call[0][0] for call in calls] == ['/bin/psql', '/bin/pg_dump', '/bin/pg_restore']
    assert all(call[1]['timeout'] == 5 for call in calls)


def test_database_target_cleanup_requires_exact_name_and_ownership():
    owned = {'base2_test_policy_abc': 'nonce'}
    for name, marker, owner in [('mydatabase', 'nonce', True),
                                ('base2_test_policy_abc', 'other', True),
                                ('base2_test_policy_abc', 'nonce', False)]:
        with pytest.raises(fixture.RestoreFixtureError, match='ownership_mismatch'):
            fixture.verify_owned_target(name, marker, owner, owned)
    fixture.verify_owned_target('base2_test_policy_abc', 'nonce', True, owned)


def test_unverified_restore_cannot_open_runtime_pool(monkeypatch):
    with (
        pytest.raises(fixture.RestoreFixtureError, match='security_not_verified'),
        fixture.runtime_database('base2_restore_policy_test', monkeypatch, verified=False),
    ):
        pytest.fail('unverified runtime entry')


def test_runtime_switch_restores_original_pools_after_nested_fixture_patch(monkeypatch):
    from api import db
    old = object()
    monkeypatch.setattr(db, '_pool', old)
    class Pool:
        closed = False
        def closeall(self): self.closed = True
    pool = Pool()
    with fixture.runtime_database('base2_test_policy_test', monkeypatch, verified=True) as patch:
        patch.setattr(db, '_pool', pool)
    assert pool.closed
    assert db._pool is old


def test_zero_execution_missing_receipt_cannot_pass(monkeypatch, tmp_path):
    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_RUN_ID', 'a' * 32)
    with pytest.raises(fixture.RestoreFixtureError, match='execution_receipt_missing'):
        fixture.verify_report(tmp_path / 'missing.json')


def test_stale_or_zero_count_receipt_cannot_pass(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_RUN_ID', 'a' * 32)
    monkeypatch.setattr(fixture.subprocess, 'check_output', lambda *a, **k: 'b' * 40)
    receipt = tmp_path / 'receipt.json'
    receipt.write_text(json.dumps({'status': 'passed', 'caseCount': 0, 'runId': 'old'}))
    with pytest.raises(fixture.RestoreFixtureError, match='execution_receipt_invalid'):
        fixture.verify_report(receipt)


def test_ci_dedicated_restore_requires_real_execution_and_preserves_normal_slice():
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[2]
    steps = yaml.safe_load((root / '.github/workflows/ci-backend.yml').read_text())['jobs']['backend-integration']['steps']
    ordinary = next(step for step in steps if step.get('name') == 'Run API integration tests')
    assert '--ignore=tests/test_workspace_policy_restore_postgres.py' in ordinary['run']
    dedicated = next(step for step in steps if step.get('name') == 'Restore Feature124 into separate owned database')
    assert dedicated['env']['WORKSPACE_RESTORE_DISPOSABLE'] == '1'
    assert dedicated['env']['WORKSPACE_POLICY_DISPOSABLE'] == '1'
    assert 'timeout 300 python -m pytest api/tests/test_workspace_policy_restore_postgres.py' in dedicated['run']
    assert '--verify-report "$WORKSPACE_RESTORE_REPORT"' in dedicated['run']
    assert 'continue-on-error' not in dedicated
    assert dedicated['timeout-minutes'] == 6


def test_docker_runner_explicit_restore_mode_cannot_fake_pass(monkeypatch):
    from scripts.python import run_workspace_postgres_acceptance as runner
    monkeypatch.setattr(runner.sys, 'argv', ['acceptance', '--restore-security'])
    with pytest.raises(RuntimeError, match='requires_host_combined_dependencies'):
        runner.main()


def test_backup_process_timeout_is_bounded_and_not_a_mocked_backup(monkeypatch):
    seen = []
    def run(command, **kwargs):
        seen.append(kwargs['timeout'])
        return subprocess.CompletedProcess(command, 0, '', '')
    monkeypatch.setattr(fixture.subprocess, 'run', run)
    fixture.bounded_runner(['pg_dump'], timeout=3600)
    fixture.bounded_runner(['psql'], timeout=5)
    assert seen == [30, 5]


def test_cleanup_attempts_every_owned_target_without_force_or_new_grants(monkeypatch):
    from contextlib import contextmanager
    h = object.__new__(fixture.DisposableRestore)
    h.main = 'untouched-main'
    h.owned = {'base2_test_policy_a': 'a', 'base2_restore_policy_b': 'b'}
    calls = []
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, query, params=()):
            calls.append((str(query), params))
            self.name = params[0] if params else None
        def fetchone(self):
            return ('wrong' if self.name.endswith('_b') else 'a', True)
    class Connection:
        def cursor(self): return Cursor()
    @contextmanager
    def owner(database):
        assert database == h.main
        yield Connection()
    monkeypatch.setattr(h, 'owner', owner)
    with pytest.raises(fixture.RestoreFixtureError, match='cleanup_failed'):
        h.cleanup()
    assert [params[0] for query, params in calls if params] == list(reversed(h.owned))
    drops = [query for query, params in calls if 'DROP DATABASE' in query]
    assert len(drops) == 1 and 'base2_test_policy_a' in drops[0]
    assert 'FORCE' not in drops[0]
    h.cleanup(primary_failure=True)  # Preserve original failure rather than masking it.


def test_recovery_source_contracts_are_explicitly_collected_in_api_ci():
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / '.github/workflows/ci-backend.yml').read_text())
    steps = workflow['jobs']['backend']['steps'] if 'backend' in workflow['jobs'] else next(
        job['steps'] for job in workflow['jobs'].values()
        if job.get('strategy', {}).get('matrix', {}).get('service') == ['api', 'django']
    )
    step = next(item for item in steps if item.get('name') == 'Recovery security and disposable harness contracts')
    assert step['if'] == "matrix.service == 'api'"
    for name in ('test_production_backup.py', 'test_recovery_assurance.py',
                 'test_backup_security_manifest.py', 'test_workspace_policy_restore_contract.py'):
        assert 'scripts/tests/' + name in step['run']
    assert 'continue-on-error' not in step


def test_changed_recovery_scripts_keep_native_lint_and_type_gates():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / '.github/workflows/ci-backend.yml').read_text())
    steps = next(job['steps'] for job in workflow['jobs'].values()
                 if job.get('strategy', {}).get('matrix', {}).get('service') == ['api', 'django'])
    command = next(item['run'] for item in steps if item.get('name') ==
                   'Recovery security and disposable harness contracts')
    for module in ('production_backup', 'recovery_assurance', 'backup_security_manifest',
                   'workspace_policy_restore_fixture'):
        for tool in ('ruff check', 'mypy'):
            assert any(line.startswith('python -m ' + tool) and
                       f'scripts/python/{module}.py' in line for line in command.splitlines())


def test_full_gate_keeps_existing_backup_contract_and_collects_new_security_tests():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    checks = json.loads((root / 'scripts/config/complete-gate-v1.json').read_text())['checks']
    check = next(item for item in checks if item['id'] == 'production-backup-contract')
    assert check['required'] is True and check['timeoutSeconds'] == 60
    assert check['dependsOn'] == ['recovery-assurance-contract']
    for name in ('test_production_backup.py', 'test_backup_security_manifest.py',
                 'test_workspace_policy_restore_contract.py'):
        assert 'scripts/tests/' + name in check['command']


def test_harness_cannot_target_remote_host_even_with_flags(monkeypatch, tmp_path):
    for key, value in {'WORKSPACE_POLICY_DISPOSABLE': '1', 'WORKSPACE_RESTORE_DISPOSABLE': '1',
                       'DB_NAME': 'database', 'DB_USER': 'owner', 'DB_PASSWORD': 'synthetic',
                       'DB_HOST': 'production.example.test'}.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(fixture.RestoreFixtureError, match='host_must_be_loopback'):
        fixture.DisposableRestore(tmp_path)


def test_dedicated_restore_prefers_only_complete_existing_server16_toolset():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / '.github/workflows/ci-backend.yml').read_text())
    step = next(item for item in workflow['jobs']['backend-integration']['steps']
                if item.get('name') == 'Restore Feature124 into separate owned database')
    run = step['run']
    for tool in ('psql', 'pg_dump', 'pg_restore'):
        assert f'[ -x /usr/lib/postgresql/16/bin/{tool} ]' in run
    assert run.index('export PATH="/usr/lib/postgresql/16/bin:$PATH"') < run.index(
        'python -m scripts.python.workspace_policy_restore_fixture') < run.index('timeout 300')
    assert all(command not in run for command in ('apt-get', 'curl ', 'wget '))


def test_service_file_uses_libpq_delimiters_and_preserves_values(monkeypatch, tmp_path):
    """libpq compares keys verbatim before '=', unlike Python ConfigParser."""
    import configparser
    from unittest.mock import MagicMock

    from scripts.python import production_backup

    for key, value in {
        'WORKSPACE_POLICY_DISPOSABLE': '1', 'WORKSPACE_RESTORE_DISPOSABLE': '1',
        'DB_NAME': 'main', 'DB_HOST': 'localhost', 'DB_USER': 'fixture_owner',
        'DB_PASSWORD': 'synthetic=percent%value',
        **{prefix + '_DB_USER': prefix.lower() for prefix in fixture.ROLE_KEYS},
    }.items():
        monkeypatch.setenv(key, value)
    harness = fixture.DisposableRestore(tmp_path)
    owner = MagicMock()
    cursor = owner.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [('fixture_owner',)]
    cursor.fetchone.return_value = (41,)
    monkeypatch.setattr(harness, 'owner', owner)
    monkeypatch.setattr(fixture.subprocess, 'check_output', lambda *a, **k: 'a' * 40)
    monkeypatch.setattr(production_backup, 'load_config', lambda path: path)
    harness.config()
    service = tmp_path / 'pg-service.conf'
    text = service.read_text()
    for line in text.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            assert key == key.strip()
            assert value == value.lstrip()
    parsed = configparser.RawConfigParser()
    parsed.read_string(text)
    for section, database in [('source', harness.source), ('target', harness.target)]:
        assert parsed[section]['host'] == 'localhost'
        assert parsed[section]['dbname'] == database
        assert parsed[section]['password'] == 'synthetic=percent%value'
        assert parsed[section]['options'] == '-c statement_timeout=5000 -c lock_timeout=5000'
    assert service.stat().st_mode & 0o777 == 0o600


def test_workspace_runner_collects_public_pack_key_regressions():
    import inspect

    from scripts.python import run_workspace_postgres_acceptance as runner

    source = inspect.getsource(runner.main)
    policy_check = source.split('policy_check = media_check[:-1] + [', 1)[1].split('run(policy_check)', 1)[0]
    assert '"api/tests/test_workspace_type_keys_postgres.py"' in policy_check
    assert '"api/tests/test_public_pack_search_postgres.py"' in policy_check
    assert '"api/tests/test_content_public_authoring_postgres.py"' in policy_check
    assert '"api/tests/test_workspace_policy_postgres.py"' in policy_check
    assert '"WORKSPACE_POLICY_DISPOSABLE=1"' in policy_check
    assert 'test_workspace_policy_restore_postgres.py' not in policy_check


def test_restore_diagnostic_is_independent_but_never_masks_core_failure():
    import yaml

    workflow = yaml.safe_load((fixture.ROOT / '.github/workflows/ci-backend.yml').read_text())
    steps = next(job['steps'] for job in workflow['jobs'].values()
                 if any(step.get('name') == 'Run API integration tests' for step in job.get('steps', [])))
    core = next(step for step in steps if step.get('name') == 'Run API integration tests')
    restore = next(step for step in steps if step.get('name') == 'Restore Feature124 into separate owned database')
    receipt = next(step for step in steps if step.get('name') == 'Retain successful isolated restoration evidence')
    assert core['id'] == 'integration_core'
    assert not core.get('continue-on-error', False)
    assert restore['id'] == 'workspace_restore'
    assert restore['if'] == "${{ !cancelled() && (steps.integration_core.outcome == 'success' || steps.integration_core.outcome == 'failure') }}"
    assert not restore.get('continue-on-error', False)
    assert receipt['if'] == "${{ !cancelled() && steps.workspace_restore.outcome == 'success' }}"


def test_failed_restore_retains_only_sanitized_bound_diagnostic(monkeypatch, tmp_path):
    import json

    from scripts.python.backup_security_manifest import catalog_difference

    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '1')
    run_id = 'a' * 32
    path = tmp_path / f'workspace-policy-failure-{run_id}.json'
    monkeypatch.setenv('WORKSPACE_RESTORE_RUN_ID', run_id)
    monkeypatch.setenv('WORKSPACE_RESTORE_DIAGNOSTIC', str(path))
    diagnostic = catalog_difference({'databaseOwner': 'private-source'}, {'databaseOwner': 'private-target'})
    fixture.retain_restore_failure(diagnostic, source_commit='b' * 40)
    result = json.loads(path.read_text())
    assert result == {'schemaVersion': 1, 'status': 'failed', 'stage': 'restore_security_catalog',
                      'runId': run_id, 'sourceCommit': 'b' * 40, 'diagnostic': diagnostic}
    assert 'private-' not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(fixture.RestoreFixtureError, match='execution_receipt_invalid'):
        monkeypatch.setattr(fixture.subprocess, 'check_output', lambda *a, **k: 'b' * 40)
        fixture.verify_report(path)


@pytest.mark.parametrize('diagnostic', [None, {'raw': 'PRIVATE_SECRET'},
                                       {'schemaVersion': 1, 'categories': [], 'unknownCategories': 'PRIVATE_SECRET'}])
def test_untrusted_restore_diagnostic_cannot_leak(monkeypatch, tmp_path, capsys, diagnostic):
    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '1')
    run_id = 'a' * 32
    path = tmp_path / f'workspace-policy-failure-{run_id}.json'
    monkeypatch.setenv('WORKSPACE_RESTORE_RUN_ID', run_id)
    monkeypatch.setenv('WORKSPACE_RESTORE_DIAGNOSTIC', str(path))
    fixture.retain_restore_failure(diagnostic, source_commit='b' * 40)
    assert not path.exists()
    output = capsys.readouterr()
    assert 'PRIVATE_SECRET' not in output.out + output.err
    assert 'restore_fixture:diagnostic_unavailable' in output.err


def test_restore_parity_error_is_reraised_without_success(monkeypatch, tmp_path):
    from scripts.python import production_backup
    from scripts.python.backup_security_manifest import SecurityManifestError

    harness = object.__new__(fixture.DisposableRestore)
    harness.root, harness.target, harness.security_verified = tmp_path, 'owned_target', False
    config = {'receiptRoot': str(tmp_path), 'pgServiceFile': str(tmp_path / 'service'), 'sourceCommit': 'b' * 40}
    monkeypatch.setattr(harness, 'config', lambda: config)
    monkeypatch.setattr(production_backup, 'create_production_backup', lambda *a, **k: {'backupFile': 'owned.tar.enc'})
    failure = SecurityManifestError('security:catalog_mismatch', diagnostic={'sentinel': True})
    def restore(*args, **kwargs):
        raise failure
    monkeypatch.setattr(production_backup, 'restore_database_isolated', restore)
    retained = []
    monkeypatch.setattr(fixture, 'retain_restore_failure', lambda value, **kwargs: retained.append((value, kwargs)))
    with pytest.raises(SecurityManifestError) as raised:
        harness.backup_restore()
    assert raised.value is failure
    assert retained == [(failure.diagnostic, {'source_commit': 'b' * 40})]
    assert harness.security_verified is False


def test_failed_restore_artifact_is_separate_and_never_success_evidence():
    import yaml

    steps = yaml.safe_load((fixture.ROOT / '.github/workflows/ci-backend.yml').read_text())['jobs']['backend-integration']['steps']
    failed = next(step for step in steps if step.get('name') == 'Retain failed isolated restoration diagnostic')
    success = next(step for step in steps if step.get('name') == 'Retain successful isolated restoration evidence')
    assert failed['if'] == "${{ !cancelled() && steps.workspace_restore.outcome == 'failure' }}"
    assert failed['with']['if-no-files-found'] == 'warn'
    assert failed['with']['path'].endswith('/workspace-policy-failure-*.json')
    assert failed['with']['name'] != success['with']['name']
    assert 'failure' not in success['with']['path']


def test_diagnostic_write_failure_never_overwrites_existing_evidence(monkeypatch, tmp_path, capsys):
    from scripts.python.backup_security_manifest import catalog_difference

    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '1')
    run_id = 'a' * 32
    path = tmp_path / f'workspace-policy-failure-{run_id}.json'
    path.write_text('prior evidence')
    monkeypatch.setenv('WORKSPACE_RESTORE_RUN_ID', run_id)
    monkeypatch.setenv('WORKSPACE_RESTORE_DIAGNOSTIC', str(path))
    diagnostic = catalog_difference({'databaseOwner': 'before'}, {'databaseOwner': 'after'})
    fixture.retain_restore_failure(diagnostic, source_commit='b' * 40)
    assert path.read_text() == 'prior evidence'
    assert capsys.readouterr().err == 'restore_fixture:diagnostic_unavailable\n'


@pytest.mark.parametrize('invalid', ['run', 'commit', 'path', 'guard'])
def test_failure_diagnostic_requires_owned_run_binding(monkeypatch, tmp_path, invalid):
    from scripts.python.backup_security_manifest import catalog_difference

    monkeypatch.setenv('WORKSPACE_POLICY_DISPOSABLE', '1')
    monkeypatch.setenv('WORKSPACE_RESTORE_DISPOSABLE', '0' if invalid == 'guard' else '1')
    run_id = 'a' * 32
    path = tmp_path / ('wrong.json' if invalid == 'path' else f'workspace-policy-failure-{run_id}.json')
    monkeypatch.setenv('WORKSPACE_RESTORE_RUN_ID', 'invalid' if invalid == 'run' else run_id)
    monkeypatch.setenv('WORKSPACE_RESTORE_DIAGNOSTIC', str(path))
    fixture.retain_restore_failure(catalog_difference({}, {}),
                                   source_commit='invalid' if invalid == 'commit' else 'b' * 40)
    assert not path.exists()
