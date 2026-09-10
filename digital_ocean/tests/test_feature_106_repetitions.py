from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from digital_ocean.scripts.python import feature_106_repetitions as repetitions


@contextmanager
def _same_source(root: Path, _commit: str, _parent: Path):
    yield root


def _prepare_run(monkeypatch, commit: str) -> None:
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: commit)
    monkeypatch.setattr(repetitions, "_require_exact_source", lambda _root, _commit: None)
    monkeypatch.setattr(repetitions, "_isolated_source", _same_source)


def test_exact_head_evidence_is_hash_bound_and_replay_safe(tmp_path, monkeypatch):
    commit = "a" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 2)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["sourceCommit"] == commit
    assert payload["repetitionsPerSuite"] == 2
    assert len(payload["files"]) == 2
    assert len(payload["evidenceDigest"]) == 64
    assert repetitions.run(tmp_path) == result


def test_existing_evidence_rejects_changed_member(tmp_path, monkeypatch):
    commit = "b" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    (result.parent / "suite-1.log").write_text("changed\n", encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="changed"):
        repetitions.run(tmp_path)


def test_existing_evidence_rejects_manifest_tamper(tmp_path, monkeypatch):
    commit = "d" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["suiteCommands"] = {"suite": ["changed"]}
    result.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions.run(tmp_path)


def test_source_commit_is_exact_and_fail_closed(tmp_path, monkeypatch):
    class Result:
        returncode = 0
        stdout = "e" * 40 + "\n"

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    assert repetitions._source_commit(tmp_path) == "e" * 40
    Result.stdout = "not-a-commit\n"
    with pytest.raises(repetitions.RepetitionError, match="source_unavailable"):
        repetitions._source_commit(tmp_path)


def test_native_windows_fails_before_evidence_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(repetitions, "os", SimpleNamespace(name="nt"))
    with pytest.raises(repetitions.RepetitionError, match="platform_unsupported"):
        repetitions.run(tmp_path)
    assert not (tmp_path / ".artifacts").exists()


def test_structurally_invalid_existing_manifest_is_rejected(tmp_path, monkeypatch):
    commit = "f" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    result.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions.run(tmp_path)


def test_missing_existing_manifest_is_rejected(tmp_path):
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions._validate_existing(tmp_path, "f" * 40)


def test_main_reports_success_and_sanitized_failure(monkeypatch, capsys, tmp_path):
    result = tmp_path / "result.json"
    monkeypatch.setattr(repetitions, "run", lambda: result)
    assert repetitions.main() == 0
    assert str(result) in capsys.readouterr().out

    def fail():
        raise repetitions.RepetitionError("bounded_failure")

    monkeypatch.setattr(repetitions, "run", fail)
    assert repetitions.main() == 2
    assert "ERROR:RepetitionError:bounded_failure" in capsys.readouterr().out


def test_validate_only_admits_exact_current_bundle(monkeypatch, tmp_path):
    result = tmp_path / "result.json"
    monkeypatch.setattr(repetitions, "validate_current", lambda: result)
    assert repetitions.main(["--validate-existing"]) == 0
    assert repetitions.main(["--unknown"]) == 2


def test_dirty_source_and_failed_repetition_are_terminal(tmp_path, monkeypatch):
    with pytest.raises(repetitions.RepetitionError, match="not_clean"):
        monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "dirty\n"}
        )())
        repetitions._require_clean(tmp_path)

    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, "c" * 40)
    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: type(
        "Result", (), {"returncode": 1, "stdout": "", "stderr": "failed\n"}
    )())
    with pytest.raises(repetitions.RepetitionError, match="repetition_failed.*evidence="):
        repetitions.run(tmp_path)
    manifests = list((tmp_path / ".artifacts" / "feature-106-repetitions" / "failures").rglob("result.json"))
    assert len(manifests) == 1
    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    member = manifests[0].parent / "failure.log"
    assert payload["status"] == "failed"
    assert payload["sourceCommit"] == "c" * 40
    assert payload["suite"] == "suite"
    assert payload["exitCode"] == 1
    assert member.read_text(encoding="utf-8") == "failed\n"
    assert payload["logSha256"] == repetitions._digest(member)


def test_failure_evidence_replay_is_idempotent_and_tamper_evident(tmp_path):
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir(mode=0o700)
    arguments = (
        evidence_root,
        "d" * 40,
        "suite",
        3,
        ("pytest", "fixture.py"),
        1,
        b"bounded failure\n",
    )
    first = repetitions._persist_failure(*arguments)
    assert repetitions._persist_failure(*arguments) == first
    (first.parent / "failure.log").write_bytes(b"tampered\n")
    with pytest.raises(repetitions.RepetitionError, match="failure_evidence_changed"):
        repetitions._persist_failure(*arguments)


def test_failure_evidence_is_bounded_and_rejects_manifest_or_mode_drift(tmp_path):
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir(mode=0o700)
    arguments = (
        evidence_root,
        "e" * 40,
        "suite",
        4,
        ("pytest", "fixture.py"),
        2,
        b"x" * (1024 * 1024 + 1),
    )
    manifest = repetitions._persist_failure(*arguments)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["bytes"] == 1024 * 1024
    assert payload["outputTruncated"] is True
    manifest.write_text("{bad-json", encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="failure_evidence_changed"):
        repetitions._persist_failure(*arguments)

    manifest.write_text(json.dumps(payload), encoding="utf-8")
    manifest.chmod(0o644)
    with pytest.raises(repetitions.RepetitionError, match="permissions_invalid"):
        repetitions._persist_failure(*arguments)


def test_failure_evidence_rejects_symlinked_parent(tmp_path):
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir(mode=0o700)
    outside = tmp_path / "outside"
    outside.mkdir()
    (evidence_root / "failures").symlink_to(outside, target_is_directory=True)
    with pytest.raises(repetitions.RepetitionError, match="failure_evidence_invalid"):
        repetitions._persist_failure(
            evidence_root,
            "f" * 40,
            "suite",
            1,
            ("pytest",),
            1,
            b"failure\n",
        )


def test_test_environment_is_allowlisted_and_credential_free(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://owner:secret@production.invalid/app")
    monkeypatch.setenv("REDIS_URL", "redis://:secret@production.invalid/0")
    monkeypatch.setenv("AWS_PROFILE", "production")
    monkeypatch.setenv("DO_API_TOKEN", "secret")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")
    environment = repetitions._test_environment(tmp_path)
    assert environment["ENV"] == "test"
    assert environment["HOME"] == str(tmp_path)
    assert environment["NO_PROXY"] == "*"
    assert environment["PYTHONHASHSEED"] == "0"
    assert environment["PYTHONMALLOC"] == "malloc"
    assert not {
        "DATABASE_URL", "REDIS_URL", "AWS_PROFILE", "DO_API_TOKEN", "HTTPS_PROXY"
    } & environment.keys()
    assert set(environment) <= {
        "CI", "ENV", "HOME", "LANG", "LC_ALL", "NO_PROXY", "PATH",
        "PYTHONHASHSEED", "PYTHONMALLOC",
        "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "COMSPEC", "SYSTEMDRIVE",
        "SYSTEMROOT", "TEMP", "TMP", "WINDIR",
    }


def test_exact_source_change_is_terminal(tmp_path, monkeypatch):
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: "b" * 40)
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    with pytest.raises(repetitions.RepetitionError, match="source_changed"):
        repetitions._require_exact_source(tmp_path, "a" * 40)


def test_native_crash_is_retained_then_boundedly_recovered(tmp_path, monkeypatch):
    commit = "8" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)
    results = iter(
        (
            SimpleNamespace(returncode=-11, stdout="", stderr="native crash\n"),
            SimpleNamespace(returncode=0, stdout="passed\n", stderr=""),
        )
    )
    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: next(results))

    manifest = repetitions.run(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(payload["nativeCrashRecoveries"]) == 1
    recovery = payload["nativeCrashRecoveries"][0]
    failure = tmp_path / ".artifacts/feature-106-repetitions" / recovery["path"]
    assert recovery["manifestSha256"] == repetitions._digest(failure)
    assert json.loads(failure.read_text(encoding="utf-8"))["exitCode"] == -11
    assert (manifest.parent / "suite-1.log").read_text(encoding="utf-8") == "passed\n"
    assert repetitions.run(tmp_path) == manifest


def _recovered_run(tmp_path, monkeypatch):
    commit = "6" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)
    results = iter(
        (
            SimpleNamespace(returncode=139, stdout="", stderr="native crash\n"),
            SimpleNamespace(returncode=0, stdout="passed\n", stderr=""),
        )
    )
    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: next(results))
    manifest = repetitions.run(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    recovery = payload["nativeCrashRecoveries"][0]
    failure = tmp_path / ".artifacts/feature-106-repetitions" / recovery["path"]
    return commit, manifest, payload, recovery, failure


@pytest.mark.parametrize("target", ["manifest", "log"])
def test_recovered_replay_rejects_missing_or_changed_collateral(
    tmp_path, monkeypatch, target
):
    _commit, _manifest, _payload, _recovery, failure = _recovered_run(
        tmp_path, monkeypatch
    )
    member = failure if target == "manifest" else failure.parent / "failure.log"
    if target == "manifest":
        member.unlink()
    else:
        member.write_bytes(b"tampered\n")
    with pytest.raises(repetitions.RepetitionError, match="recovery_evidence"):
        repetitions.run(tmp_path)


def test_recovered_replay_rejects_symlinked_collateral(tmp_path, monkeypatch):
    _commit, _manifest, _payload, _recovery, failure = _recovered_run(
        tmp_path, monkeypatch
    )
    member = failure.parent / "failure.log"
    outside = tmp_path / "outside.log"
    outside.write_bytes(member.read_bytes())
    member.unlink()
    member.symlink_to(outside)
    with pytest.raises(repetitions.RepetitionError, match="recovery_evidence"):
        repetitions.run(tmp_path)


def test_recovered_replay_rejects_public_collateral_mode(tmp_path, monkeypatch):
    _commit, _manifest, _payload, _recovery, failure = _recovered_run(
        tmp_path, monkeypatch
    )
    failure.chmod(0o644)
    with pytest.raises(repetitions.RepetitionError, match="permissions_invalid"):
        repetitions.run(tmp_path)


@pytest.mark.parametrize(
    "mutation", ["traversal", "wrong_commit", "invalid_exit", "duplicate"]
)
def test_recovered_replay_rejects_identity_substitution(
    tmp_path, monkeypatch, mutation
):
    commit, manifest, payload, recovery, failure = _recovered_run(tmp_path, monkeypatch)
    if mutation == "duplicate":
        payload["nativeCrashRecoveries"].append(recovery.copy())
    elif mutation == "invalid_exit":
        failure_payload = json.loads(failure.read_text(encoding="utf-8"))
        failure_payload["exitCode"] = 1
        digest_payload = {
            key: value for key, value in failure_payload.items() if key != "evidenceDigest"
        }
        failure_payload["evidenceDigest"] = repetitions.hashlib.sha256(
            json.dumps(digest_payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        failure.write_text(json.dumps(failure_payload), encoding="utf-8")
        recovery["manifestSha256"] = repetitions._digest(failure)
    elif mutation == "wrong_commit":
        recovery["path"] = recovery["path"].replace(commit, "5" * 40)
    else:
        recovery["path"] = f"failures/{commit}/../{failure.parent.name}/result.json"
    digest_payload = {key: value for key, value in payload.items() if key != "evidenceDigest"}
    payload["evidenceDigest"] = repetitions.hashlib.sha256(
        json.dumps(digest_payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="recovery_evidence"):
        repetitions.run(tmp_path)


def test_native_crash_exhaustion_retains_every_attempt(tmp_path, monkeypatch):
    commit = "7" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)
    calls = 0

    def crash(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(returncode=-11, stdout="", stderr="native crash\n")

    monkeypatch.setattr(repetitions.subprocess, "run", crash)
    with pytest.raises(repetitions.RepetitionError, match="repetition_failed"):
        repetitions.run(tmp_path)
    manifests = list(
        (tmp_path / ".artifacts/feature-106-repetitions/failures").rglob("result.json")
    )
    assert calls == repetitions.MAX_NATIVE_ATTEMPTS
    assert len(manifests) == repetitions.MAX_NATIVE_ATTEMPTS
    assert {json.loads(path.read_text(encoding="utf-8"))["attempt"] for path in manifests} == {
        1,
        2,
        3,
    }


def test_existing_evidence_rejects_symlinked_member(tmp_path, monkeypatch):
    commit = "9" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    member = result.parent / "suite-1.log"
    replacement = tmp_path / "replacement.log"
    replacement.write_bytes(member.read_bytes())
    member.unlink()
    member.symlink_to(replacement)
    with pytest.raises(repetitions.RepetitionError, match="invalid|changed"):
        repetitions.run(tmp_path)


def test_isolated_source_uses_detached_exact_commit(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess = repetitions.subprocess
    subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"],
        cwd=repository, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Fixture"],
        cwd=repository, check=True, capture_output=True,
    )
    (repository / "tracked.txt").write_text("exact\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=repository, check=True, capture_output=True,
    )
    commit = repetitions._source_commit(repository)
    stage = tmp_path / "stage"
    stage.mkdir()
    with repetitions._isolated_source(repository, commit, stage) as source:
        assert source != repository
        assert (source / "tracked.txt").read_text(encoding="utf-8") == "exact\n"
        assert repetitions._source_commit(source) == commit
    assert not (stage / "source").exists()


def test_windows_test_environment_keeps_only_process_primitives(tmp_path, monkeypatch):
    fake_os = SimpleNamespace(
        name="nt",
        environ={
            "COMSPEC": r"C:\Windows\System32\cmd.exe",
            "SYSTEMROOT": r"C:\Windows",
            "DATABASE_URL": "postgresql://owner:secret@production.invalid/app",
        },
    )
    monkeypatch.setattr(repetitions, "os", fake_os)
    environment = repetitions._test_environment(tmp_path)
    assert environment["COMSPEC"].endswith("cmd.exe")
    assert environment["SYSTEMROOT"] == r"C:\Windows"
    assert "DATABASE_URL" not in environment


def test_isolated_source_add_and_cleanup_fail_closed(tmp_path, monkeypatch):
    class Result:
        def __init__(self, returncode):
            self.returncode = returncode

    monkeypatch.setattr(
        repetitions.subprocess,
        "run",
        lambda *_args, **_kwargs: Result(1),
    )
    with (
        pytest.raises(repetitions.RepetitionError, match="isolation_failed"),
        repetitions._isolated_source(tmp_path, "a" * 40, tmp_path / "stage"),
    ):
        pass

    outcomes = iter((Result(0), Result(1)))
    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: next(outcomes))
    monkeypatch.setattr(repetitions, "_require_exact_source", lambda *_args: None)
    with (
        pytest.raises(repetitions.RepetitionError, match="cleanup_failed"),
        repetitions._isolated_source(tmp_path, "a" * 40, tmp_path / "stage"),
    ):
        pass


def test_existing_evidence_rejects_symlinked_root_and_malformed_json(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / ("a" * 40)
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions._validate_existing(linked, "a" * 40)

    manifest = target / "result.json"
    manifest.write_text("{not-json", encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions._validate_existing(target, "a" * 40)


def test_private_evidence_root_rejects_symlinked_ancestor(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / ".artifacts").symlink_to(outside, target_is_directory=True)
    with pytest.raises(repetitions.RepetitionError, match="root_invalid"):
        repetitions._private_evidence_root(project)


def test_private_evidence_root_rejects_nondirectory_ancestor(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".artifacts").write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="root_invalid"):
        repetitions._private_evidence_root(project)


def test_existing_evidence_rejects_permission_drift(tmp_path, monkeypatch):
    commit = "8" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    _prepare_run(monkeypatch, commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    result.chmod(0o644)
    with pytest.raises(repetitions.RepetitionError, match="permissions_invalid"):
        repetitions.run(tmp_path)
