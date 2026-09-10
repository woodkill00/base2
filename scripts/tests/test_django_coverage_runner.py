from __future__ import annotations

from stat import S_IMODE
from types import SimpleNamespace

import pytest

from scripts.python import run_django_coverage as runner


def test_native_crashes_are_bounded_and_partial_reports_removed(tmp_path, monkeypatch, capsys):
    report = tmp_path / "django.json"
    prefix = tmp_path / ".coverage.django"
    results = iter((-11, 139, 0))
    calls = 0
    accepted = set()

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
    assert (
        runner.run_bounded(
            ["fixed"], {}, report, parallel_prefix=prefix, accepted_shards=accepted
        )
        == 3
    )
    assert calls == 3
    assert not (tmp_path / ".coverage.django.attempt-1").exists()
    assert not (tmp_path / ".coverage.django.attempt-2").exists()
    assert (tmp_path / ".coverage.django.attempt-3").is_file()
    assert accepted == {tmp_path / ".coverage.django.attempt-3"}
    assert S_IMODE((tmp_path / ".coverage.django.attempt-3").stat().st_mode) == 0o600
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


def test_successful_symlink_shard_fails_closed_and_preserves_target(tmp_path, monkeypatch):
    prefix = tmp_path / ".coverage.django"
    target = tmp_path / "outside-coverage-data"
    target.write_text("preserve", encoding="utf-8")

    def execute(_command, **_kwargs):
        (tmp_path / ".coverage.django.success").symlink_to(target)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="django_coverage_shard_invalid"):
        runner.run_bounded(
            ["fixed"], {}, tmp_path / "django.json", parallel_prefix=prefix
        )
    assert target.read_text(encoding="utf-8") == "preserve"
    assert not (tmp_path / ".coverage.django.success").exists()


def test_successful_directory_shard_fails_closed(tmp_path, monkeypatch):
    prefix = tmp_path / ".coverage.django"

    def execute(_command, **_kwargs):
        (tmp_path / ".coverage.django.directory").mkdir()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="django_coverage_shard_invalid"):
        runner.run_bounded(
            ["fixed"], {}, tmp_path / "django.json", parallel_prefix=prefix
        )


@pytest.mark.parametrize("size", [0, runner.MAX_SHARD_BYTES + 1])
def test_successful_empty_or_oversized_shard_fails_closed(tmp_path, monkeypatch, size):
    prefix = tmp_path / ".coverage.django"
    shard = tmp_path / ".coverage.django.invalid-size"

    def execute(_command, **_kwargs):
        shard.write_bytes(b"")
        with shard.open("r+b") as handle:
            handle.truncate(size)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="django_coverage_shard_invalid"):
        runner.run_bounded(
            ["fixed"], {}, tmp_path / "django.json", parallel_prefix=prefix
        )
    assert not shard.exists()


def test_successful_attempt_with_multiple_shards_fails_closed(tmp_path, monkeypatch):
    prefix = tmp_path / ".coverage.django"

    def execute(_command, **_kwargs):
        (tmp_path / ".coverage.django.first").write_text("one", encoding="utf-8")
        (tmp_path / ".coverage.django.second").write_text("two", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError, match="django_coverage_shard_count_invalid"):
        runner.run_bounded(
            ["fixed"], {}, tmp_path / "django.json", parallel_prefix=prefix
        )
    assert not list(tmp_path.glob(".coverage.django.*"))


def test_complete_shard_inventory_is_exact_private_and_bounded(tmp_path):
    prefix = tmp_path / ".coverage.django"
    shard = tmp_path / ".coverage.django.valid"
    shard.write_text("coverage", encoding="utf-8")
    shard.chmod(0o600)
    runner._validate_complete_shards(prefix, {shard})

    extra = tmp_path / ".coverage.django.extra"
    extra.write_text("coverage", encoding="utf-8")
    extra.chmod(0o600)
    with pytest.raises(RuntimeError, match="django_coverage_inventory_invalid"):
        runner._validate_complete_shards(prefix, {shard})


def test_complete_shard_inventory_rejects_non_private_file(tmp_path):
    prefix = tmp_path / ".coverage.django"
    shard = tmp_path / ".coverage.django.public"
    shard.write_text("coverage", encoding="utf-8")
    shard.chmod(0o644)
    with pytest.raises(RuntimeError, match="django_coverage_shard_invalid"):
        runner._validate_complete_shards(prefix, {shard})


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
