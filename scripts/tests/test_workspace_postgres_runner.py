from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from scripts.python import run_workspace_postgres_acceptance as runner


def test_idempotent_migration_recovers_only_native_failures(monkeypatch, capsys):
    results = iter((-11, 139, 0))
    calls = []

    def execute(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(runner.subprocess, "run", execute)
    result = runner.run_idempotent_native_safe(["fixed", "migration"], stdout=subprocess.DEVNULL)
    assert result.returncode == 0
    assert len(calls) == 3
    assert all(call[1]["check"] is False for call in calls)
    assert "retry 2/3" in capsys.readouterr().out


@pytest.mark.parametrize("returncode,expected_calls", [(1, 1), (-11, 3), (134, 3), (139, 3)])
def test_idempotent_migration_fails_on_assertion_or_native_exhaustion(
    monkeypatch, returncode, expected_calls
):
    calls = 0

    def execute(_command, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(subprocess.CalledProcessError) as captured:
        runner.run_idempotent_native_safe(["fixed", "migration"])
    assert captured.value.returncode == returncode
    assert calls == expected_calls


def test_only_disposable_migrations_use_native_retry():
    source = runner.Path(runner.__file__).read_text(encoding="utf-8")
    assert "MAX_NATIVE_ATTEMPTS = 3" in source
    assert "NATIVE_FAILURES = {-11, 134, 139}" in source
    assert '"PYTHONHASHSEED=0"' in source
    assert '"PYTHONMALLOC=malloc"' in source
    assert source.count("run_idempotent_native_safe(") == 9
    assert 'run(role_check + ["api-reversed"])' in source
    assert 'run(media_check + ["forward"])' in source
