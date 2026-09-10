from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.python import run_django_coverage as runner


def test_native_crashes_are_bounded_and_partial_reports_removed(tmp_path, monkeypatch, capsys):
    report = tmp_path / "django.json"
    results = iter((-11, 139, 0))
    calls = 0

    def execute(_command, **kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["check"] is False
        report.write_text("partial", encoding="utf-8")
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(runner.subprocess, "run", execute)
    assert runner.run_bounded(["fixed"], {}, report) == 3
    assert calls == 3
    assert "retry 2/3" in capsys.readouterr().out


@pytest.mark.parametrize("returncode,expected_calls", [(1, 1), (-11, 3), (134, 3), (139, 3)])
def test_assertion_failure_is_immediate_and_native_exhaustion_is_terminal(
    tmp_path, monkeypatch, returncode, expected_calls
):
    calls = 0

    def execute(_command, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match=f"exit_{returncode}"):
        runner.run_bounded(["fixed"], {}, tmp_path / "django.json")
    assert calls == expected_calls


def test_source_uses_sysmon_deterministic_runtime_and_fixed_suite():
    source = runner.Path(runner.__file__).read_text(encoding="utf-8")
    assert 'environment["COVERAGE_CORE"] = "sysmon"' in source
    assert 'environment["PYTHONHASHSEED"] = "0"' in source
    assert 'environment["PYTHONMALLOC"] = "malloc"' in source
    assert '"django/tests"' in source
    assert '"django/pytest.ini"' in source
    assert '"addopts="' in source
    assert 'rglob("test_*.py")' in source
    assert '"--parallel-mode"' in source
    assert '"--source=project,users,common,catalog,api_schema"' in source
    assert '"no:cov"' in source
    assert '"coverage", "combine", "--keep"' in source
    assert '"coverage", "json"' in source
