"""All restricted role tests use the existing disposable bootstrap identities."""
from pathlib import Path

import yaml


def test_integration_general_worker_matches_existing_disposable_bootstrap():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / '.github/workflows/ci-backend.yml').read_text())
    steps = workflow['jobs']['backend-integration']['steps']
    test_env = next(step['env'] for step in steps if step.get('name') == 'Run API integration tests')
    bootstrap = next(step['env'] for step in steps
                     if 'RUNTIME_WORKER_DB_PASSWORD' in step.get('env', {})
                     and step.get('name') != 'Run API integration tests')
    for key in ('RUNTIME_WORKER_DB_USER', 'RUNTIME_WORKER_DB_PASSWORD'):
        assert test_env[key] == bootstrap[key]
