"""Ensure the real settings identity boundary gate remains part of PR CI."""
from pathlib import Path

import yaml


def test_identity_audit_gate_uses_isolated_postgres_and_real_runner():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / '.github/workflows/ci-backend.yml').read_text())
    job = workflow['jobs']['identity-postgres-acceptance']
    assert 'if' not in job
    assert '@sha256:' in job['services']['postgres']['image']
    assert job['env']['DB_NAME'] == 'base2_identity_test'
    assert job['services']['postgres']['env']['POSTGRES_DB'] == job['env']['DB_NAME']
    runner = next(step for step in job['steps'] if step.get('name') ==
                  'Verify organization audit boundaries on real PostgreSQL')
    assert runner['run'] == 'python scripts/python/run_identity_postgres_checks.py'
    assert 'continue-on-error' not in runner
    assert 'if' not in runner
    persistence = next(step for step in job['steps'] if step.get('name') ==
                       'Verify settings persistence and concurrent saves on real PostgreSQL')
    assert persistence['run'] == (
        'python -m pytest -c api/pytest.ini --no-cov -m integration '
        'api/tests/test_settings_postgres.py'
    )
    assert 'if' not in persistence
    assert 'continue-on-error' not in persistence
