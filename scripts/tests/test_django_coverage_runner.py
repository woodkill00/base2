from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.python import run_django_coverage as runner


def test_native_crashes_are_bounded_and_partial_reports_removed(tmp_path, monkeypatch, capsys):
    report = tmp_path / "django.json"
    prefix = tmp_path / ".coverage.django"
    results = iter((-11, 139, 0))
    calls = 0

    def execute(_command, **kwargs):
        nonlocal calls
        calls += 1
        assert kwargs["check"] is False
        report.write_text("partial", encoding="utf-8")
        (tmp_path / f".coverage.django.attempt-{calls}").write_text(
            "partial", encoding="utf-8"
        )
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(runner.subprocess, "run", execute)
    assert runner.run_bounded(["fixed"], {}, report, parallel_prefix=prefix) == 3
    assert calls == 3
    assert not (tmp_path / ".coverage.django.attempt-1").exists()
    assert not (tmp_path / ".coverage.django.attempt-2").exists()
    assert (tmp_path / ".coverage.django.attempt-3").is_file()
    assert "retry 2/3" in capsys.readouterr().out


def test_ordinary_failure_removes_its_parallel_shard_without_retry(tmp_path, monkeypatch):
    prefix = tmp_path / ".coverage.django"
    calls = 0

    def execute(_command, **_kwargs):
        nonlocal calls
        calls += 1
        (tmp_path / ".coverage.django.failed").write_text("partial", encoding="utf-8")
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="exit_1"):
        runner.run_bounded(
            ["fixed"], {}, tmp_path / "django.json", parallel_prefix=prefix
        )
    assert calls == 1
    assert not (tmp_path / ".coverage.django.failed").exists()


def test_failed_symlink_shard_is_unlinked_without_touching_target(tmp_path, monkeypatch):
    prefix = tmp_path / ".coverage.django"
    target = tmp_path / "outside-coverage-data"
    target.write_text("preserve", encoding="utf-8")

    def execute(_command, **_kwargs):
        (tmp_path / ".coverage.django.failed").symlink_to(target)
        return SimpleNamespace(returncode=-11)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="django_coverage_shard_invalid"):
        runner.run_bounded(
            ["fixed"], {}, tmp_path / "django.json", parallel_prefix=prefix
        )
    assert target.read_text(encoding="utf-8") == "preserve"
    assert not (tmp_path / ".coverage.django.failed").exists()


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
