from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from digital_ocean.scripts.python.provider_lease import (
    GitRemoteLeaseStore,
    LeaseRecord,
    ProviderLeaseError,
    _network_remote_identity,
    acquire_provider_lease,
    release_provider_lease,
)
from digital_ocean.scripts.python.provider_lease import (
    _git as _lease_git,
)


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, timeout=10
    )
    return result.stdout.strip()


@pytest.fixture
def repositories(tmp_path: Path) -> tuple[Path, Path]:
    target = tmp_path / "remote.git"
    _git("init", "--bare", str(target), cwd=tmp_path)
    controller = tmp_path / "controller"
    controller.mkdir()
    _git("init", str(controller), cwd=tmp_path)
    _git("remote", "add", "origin", str(target), cwd=controller)
    return controller, target


def _store(repositories: tuple[Path, Path]) -> GitRemoteLeaseStore:
    controller, _remote = repositories
    return GitRemoteLeaseStore(repository=controller)


def _make_broker(root: Path) -> Path:
    broker = root / "provider-lease-askpass"
    broker.write_text("#!/bin/sh\nprintf '%s\\n' lease-fixture\n", encoding="utf-8")
    broker.chmod(0o700)
    return broker


def test_remote_ref_creation_is_atomic_and_exact_owner_release(repositories):
    store = _store(repositories)
    first = acquire_provider_lease(store, "base2-provision-site", "runner:first-owner-token", now=0)
    assert first.expires_at == 900
    assert first.revision
    with pytest.raises(ProviderLeaseError, match="lease_unavailable"):
        acquire_provider_lease(store, first.name, "runner:second-owner-token", now=1000)
    wrong = LeaseRecord(first.name, "runner:wrong-owner-token", first.expires_at, "0" * 40)
    with pytest.raises(ProviderLeaseError, match="owner_mismatch"):
        release_provider_lease(store, wrong)
    release_provider_lease(store, first)
    replacement = acquire_provider_lease(store, first.name, "runner:replacement-owner", now=1000)
    assert replacement.revision != first.revision


def test_crashed_and_expired_owner_remains_fail_closed(repositories):
    store = _store(repositories)
    first = acquire_provider_lease(store, "base2-provision-site", "runner:crashed-owner", now=0)
    with pytest.raises(ProviderLeaseError, match="lease_unavailable"):
        acquire_provider_lease(store, first.name, "runner:after-expiry-owner", now=5000)


def test_simultaneous_remote_claim_admits_exactly_one(repositories):
    name = "base2-provision-site"

    def claim(owner: str) -> str:
        try:
            return acquire_provider_lease(_store(repositories), name, owner, now=100).owner
        except ProviderLeaseError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(claim, ("runner:simultaneous-a", "runner:simultaneous-b")))
    assert outcomes.count("rejected") == 1
    assert len([value for value in outcomes if value.startswith("runner:")]) == 1


@pytest.mark.parametrize("remote_name", ("", "../bad", "bad name", "-option"))
def test_remote_configuration_fails_closed(remote_name: str):
    with pytest.raises(ProviderLeaseError, match="remote_invalid"):
        GitRemoteLeaseStore(remote=remote_name)


@pytest.mark.parametrize("name", ("", "../bad", "bad name", "x" * 161))
def test_lease_name_is_bounded(name: str, repositories):
    with pytest.raises(ProviderLeaseError, match="name_invalid"):
        acquire_provider_lease(_store(repositories), name, "runner:bounded-owner", now=0)


def test_environment_requires_a_dedicated_non_origin_remote(repositories, monkeypatch):
    controller, target = repositories
    monkeypatch.chdir(controller)
    monkeypatch.setenv("DO_PROVISION_LEASE_GIT_ASKPASS", str(_make_broker(target.parent)))
    monkeypatch.delenv("DO_PROVISION_LEASE_GIT_REMOTE", raising=False)
    with pytest.raises(ProviderLeaseError, match="remote_required"):
        GitRemoteLeaseStore.from_environment()
    monkeypatch.setenv("DO_PROVISION_LEASE_GIT_REMOTE", "origin")
    with pytest.raises(ProviderLeaseError, match="not_shared"):
        GitRemoteLeaseStore.from_environment()

    isolated = target.parent / "isolated.git"
    _git("init", "--bare", str(isolated), cwd=target.parent)
    _git("remote", "add", "provider-lease", str(isolated), cwd=controller)
    monkeypatch.setenv("DO_PROVISION_LEASE_GIT_REMOTE", "provider-lease")
    with pytest.raises(ProviderLeaseError, match="not_shared"):
        GitRemoteLeaseStore.from_environment()
    _git(
        "remote",
        "set-url",
        "provider-lease",
        "https://example.invalid/base2-lease.git",
        cwd=controller,
    )
    assert GitRemoteLeaseStore.from_environment().remote_identity == "example.invalid:base2-lease"


def test_environment_rejects_source_remote_alias(tmp_path: Path, monkeypatch):
    controller = tmp_path / "controller"
    controller.mkdir()
    _git("init", str(controller), cwd=tmp_path)
    _git("remote", "add", "origin", "https://example.invalid/owner/base2.git", cwd=controller)
    _git(
        "remote",
        "add",
        "provider-lease",
        "https://example.invalid/owner/base2.git",
        cwd=controller,
    )
    monkeypatch.chdir(controller)
    monkeypatch.setenv("DO_PROVISION_LEASE_GIT_ASKPASS", str(_make_broker(tmp_path)))
    monkeypatch.setenv("DO_PROVISION_LEASE_GIT_REMOTE", "provider-lease")
    with pytest.raises(ProviderLeaseError, match="not_isolated"):
        GitRemoteLeaseStore.from_environment()


@pytest.mark.parametrize(
    "url",
    (
        "http://example.invalid/lease.git",
        "https://token@example.invalid/lease.git",
        "https://example.invalid/lease.git?unsafe=1",
        "ext::sh -c unsafe",
        "file:///tmp/lease.git",
        "git@example.invalid:owner/base2-lease.git",
        "ssh://git@example.invalid/owner/base2-lease.git",
    ),
)
def test_network_remote_rejects_insecure_or_embedded_credentials(tmp_path: Path, url: str):
    controller = tmp_path / "controller"
    controller.mkdir()
    _git("init", str(controller), cwd=tmp_path)
    _git("remote", "add", "provider-lease", url, cwd=controller)
    with pytest.raises(ProviderLeaseError, match="remote_unsafe"):
        GitRemoteLeaseStore(remote="provider-lease", repository=controller)


@pytest.mark.parametrize(
    "url",
    ("git@example.invalid:owner/base2-lease.git", "ssh://git@example.invalid/owner/base2.git"),
)
def test_ssh_remote_identity_is_not_accepted(url):
    assert _network_remote_identity(url) is None


def test_global_url_rewrite_cannot_change_local_https_remote(repositories, monkeypatch, tmp_path):
    controller, _target = repositories
    _git(
        "remote",
        "set-url",
        "origin",
        "https://example.invalid/owner/provider-lease.git",
        cwd=controller,
    )
    hostile = tmp_path / "hostile.gitconfig"
    hostile.write_text(
        '[url "ssh://attacker.invalid/"]\n\tinsteadOf = https://example.invalid/\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
    store = GitRemoteLeaseStore(repository=controller)
    assert store.remote_url == "https://example.invalid/owner/provider-lease.git"


def test_git_transport_environment_is_scrubbed(monkeypatch, tmp_path):
    captured = {}

    def run(*args, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(args[0], 0, "", "")

    monkeypatch.setenv("GIT_SSH_COMMAND", "sh -c hostile")
    monkeypatch.setenv("GIT_PROXY_COMMAND", "sh -c hostile")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_ASKPASS", "hostile-askpass")
    monkeypatch.setenv("GIT_EXEC_PATH", "hostile-exec-path")
    monkeypatch.setenv("SSH_ASKPASS", "hostile-ssh-askpass")
    monkeypatch.setenv("GITHUB_TOKEN", "hostile-token")
    monkeypatch.setenv("DO_API_TOKEN", "hostile-provider-token")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "hostile-access-key")
    monkeypatch.setattr(subprocess, "run", run)
    _lease_git(["status"], cwd=tmp_path)
    assert "GIT_SSH_COMMAND" not in captured
    assert "GIT_PROXY_COMMAND" not in captured
    assert "GIT_ASKPASS" not in captured
    assert "GIT_EXEC_PATH" not in captured
    assert "SSH_ASKPASS" not in captured
    assert "GITHUB_TOKEN" not in captured
    assert "DO_API_TOKEN" not in captured
    assert "AWS_ACCESS_KEY_ID" not in captured
    assert captured["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert captured["GIT_SSL_NO_VERIFY"] == "false"


def test_explicit_askpass_broker_is_restrictive_and_works_with_real_git(tmp_path):
    broker = _make_broker(tmp_path)
    result = _lease_git(
        ["credential", "fill"],
        cwd=tmp_path,
        stdin="protocol=https\nhost=example.invalid\n\n",
        credential_broker=broker,
    )
    assert result.returncode == 0
    assert "username=lease-fixture" in result.stdout
    assert "password=lease-fixture" in result.stdout


@pytest.mark.parametrize("kind", ("missing", "relative", "permissive", "symlink"))
def test_environment_rejects_invalid_credential_broker(
    tmp_path: Path, monkeypatch, kind: str
):
    controller = tmp_path / "controller"
    controller.mkdir()
    _git("init", cwd=controller)
    _git(
        "remote", "add", "provider-lease", "https://example.invalid/lease.git", cwd=controller
    )
    monkeypatch.chdir(controller)
    monkeypatch.setenv("DO_PROVISION_LEASE_GIT_REMOTE", "provider-lease")
    broker = tmp_path / "broker"
    if kind == "missing":
        monkeypatch.delenv("DO_PROVISION_LEASE_GIT_ASKPASS", raising=False)
    elif kind == "relative":
        monkeypatch.setenv("DO_PROVISION_LEASE_GIT_ASKPASS", "broker")
    else:
        target = _make_broker(tmp_path)
        if kind == "permissive":
            target.chmod(0o755)
            broker = target
        else:
            broker.symlink_to(target)
        monkeypatch.setenv("DO_PROVISION_LEASE_GIT_ASKPASS", str(broker))
    with pytest.raises(ProviderLeaseError, match="credential_broker"):
        GitRemoteLeaseStore.from_environment()


def test_missing_remote_and_git_transport_failure_are_terminal(tmp_path: Path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git("init", cwd=repository)
    with pytest.raises(ProviderLeaseError, match="remote_unavailable"):
        GitRemoteLeaseStore(remote="provider-lease", repository=repository)

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("git", 30)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ProviderLeaseError, match="transport_failed"):
        _lease_git(["status"], cwd=repository)


@pytest.mark.parametrize(
    "owner,ttl,error",
    (
        ("short", 900, "owner_invalid"),
        ("runner:valid-owner-token", 59, "ttl_invalid"),
        ("runner:valid-owner-token", 3601, "ttl_invalid"),
    ),
)
def test_owner_and_ttl_are_bounded(repositories, owner: str, ttl: int, error: str):
    with pytest.raises(ProviderLeaseError, match=error):
        acquire_provider_lease(_store(repositories), "base2-provision-site", owner, ttl_seconds=ttl)


def test_release_requires_an_exact_revision(repositories):
    record = LeaseRecord("base2-provision-site", "runner:valid-owner-token", 1000)
    with pytest.raises(ProviderLeaseError, match="owner_mismatch"):
        release_provider_lease(_store(repositories), record)
