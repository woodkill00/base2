#!/usr/bin/env python3
"""Exact-owner remote Git compare-and-swap lease for paid provisioning.

DigitalOcean Spaces does not document conditional object creation or deletion,
so a Spaces object cannot safely serialize paid resource creation. This store
uses atomic Git ref creation and force-with-lease deletion against the already
configured source remote. Conflict, crash, drift, and stale ownership all fail
closed before another paid resource can be created.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit


class ProviderLeaseError(RuntimeError):
    pass


def _network_remote_identity(value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme in {"https", "ssh"}:
        if (
            (parsed.scheme == "https" and (parsed.username or parsed.password))
            or (parsed.scheme == "ssh" and parsed.password)
            or not parsed.hostname
            or parsed.query
            or parsed.fragment
        ):
            raise ProviderLeaseError("provider_lease_remote_unsafe")
        path = parsed.path.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return f"{parsed.hostname.lower()}:{path.lstrip('/')}"
    if parsed.scheme:
        return None
    scp = re.fullmatch(r"(?:[A-Za-z0-9._-]+@)?([A-Za-z0-9.-]+):([^\s]+)", value)
    if scp:
        path = scp.group(2).rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return f"{scp.group(1).lower()}:{path.lstrip('/')}"
    return None


@dataclass(frozen=True)
class LeaseRecord:
    name: str
    owner: str
    expires_at: int
    revision: str = ""

    def payload(self) -> bytes:
        return (
            json.dumps(
                {
                    "expiresAt": self.expires_at,
                    "name": self.name,
                    "owner": self.owner,
                    "schemaVersion": 1,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode()


def _git(
    command: list[str],
    *,
    cwd: Path,
    stdin: str | None = None,
    identity: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    if identity:
        environment.update(
            {
                "GIT_AUTHOR_NAME": "Base2 provider lease",
                "GIT_AUTHOR_EMAIL": "base2-provider-lease@invalid.local",
                "GIT_COMMITTER_NAME": "Base2 provider lease",
                "GIT_COMMITTER_EMAIL": "base2-provider-lease@invalid.local",
            }
        )
    try:
        return subprocess.run(
            ["git", *command],
            cwd=cwd,
            env=environment,
            input=stdin,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderLeaseError("provider_lease_transport_failed") from exc


class GitRemoteLeaseStore:
    """Atomic exact-owner lease held by one fixed ref on a trusted Git remote."""

    def __init__(self, *, remote: str = "origin", repository: Path | None = None) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", remote):
            raise ProviderLeaseError("provider_lease_remote_invalid")
        self.remote = remote
        self.repository = (repository or Path.cwd()).resolve()
        resolved = _git(["remote", "get-url", "--push", remote], cwd=self.repository)
        self.remote_url = resolved.stdout.strip()
        if resolved.returncode or not self.remote_url or "\n" in self.remote_url:
            raise ProviderLeaseError("provider_lease_remote_unavailable")
        self.remote_identity = _network_remote_identity(self.remote_url)
        if urlsplit(self.remote_url).scheme and self.remote_identity is None:
            raise ProviderLeaseError("provider_lease_remote_unsafe")

    @classmethod
    def from_environment(cls) -> GitRemoteLeaseStore:
        remote = os.environ.get("DO_PROVISION_LEASE_GIT_REMOTE", "").strip()
        if not remote:
            raise ProviderLeaseError("provider_lease_remote_required")
        store = cls(remote=remote)
        if store.remote_identity is None:
            raise ProviderLeaseError("provider_lease_remote_not_shared")
        source = _git(["remote", "get-url", "--push", "origin"], cwd=store.repository)
        source_identity = (
            _network_remote_identity(source.stdout.strip()) if not source.returncode else None
        )
        if source_identity is not None and source_identity == store.remote_identity:
            raise ProviderLeaseError("provider_lease_remote_not_isolated")
        return store

    @staticmethod
    def _ref(name: str) -> str:
        digest = hashlib.sha256(name.encode()).hexdigest()
        return f"refs/heads/base2-provider-leases/{digest}"

    def put_if_absent(self, record: LeaseRecord) -> LeaseRecord:
        with tempfile.TemporaryDirectory(prefix="base2-provider-lease-") as raw_root:
            root = Path(raw_root)
            if _git(["init", "--quiet"], cwd=root).returncode:
                raise ProviderLeaseError("provider_lease_local_init_failed")
            blob = _git(["hash-object", "-w", "--stdin"], cwd=root, stdin=record.payload().decode())
            if blob.returncode or not re.fullmatch(r"[0-9a-f]{40,64}\n?", blob.stdout):
                raise ProviderLeaseError("provider_lease_local_object_failed")
            tree = _git(
                ["mktree"],
                cwd=root,
                stdin=f"100644 blob {blob.stdout.strip()}\tlease.json\n",
            )
            if tree.returncode or not re.fullmatch(r"[0-9a-f]{40,64}\n?", tree.stdout):
                raise ProviderLeaseError("provider_lease_local_object_failed")
            commit = _git(
                ["commit-tree", tree.stdout.strip(), "-m", "base2 provider lease"],
                cwd=root,
                identity=True,
            )
            revision = commit.stdout.strip()
            if commit.returncode or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
                raise ProviderLeaseError("provider_lease_local_object_failed")
            pushed = _git(
                ["push", "--porcelain", self.remote_url, f"{revision}:{self._ref(record.name)}"],
                cwd=root,
            )
            if pushed.returncode:
                raise ProviderLeaseError("provider_provision_lease_unavailable")
            return replace(record, revision=revision)

    def delete_if_owner(self, record: LeaseRecord) -> None:
        if not re.fullmatch(r"[0-9a-f]{40,64}", record.revision):
            raise ProviderLeaseError("provider_provision_lease_owner_mismatch")
        with tempfile.TemporaryDirectory(prefix="base2-provider-lease-release-") as raw_root:
            root = Path(raw_root)
            if _git(["init", "--quiet"], cwd=root).returncode:
                raise ProviderLeaseError("provider_lease_local_init_failed")
            ref = self._ref(record.name)
            result = _git(
                [
                    "push",
                    "--porcelain",
                    f"--force-with-lease={ref}:{record.revision}",
                    self.remote_url,
                    f":{ref}",
                ],
                cwd=root,
            )
            if result.returncode:
                raise ProviderLeaseError("provider_provision_lease_owner_mismatch")


def acquire_provider_lease(
    store: GitRemoteLeaseStore,
    name: str,
    owner: str,
    *,
    ttl_seconds: int = 900,
    now: int | None = None,
) -> LeaseRecord:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", name):
        raise ProviderLeaseError("provider_lease_name_invalid")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{16,160}", owner):
        raise ProviderLeaseError("provider_lease_owner_invalid")
    if not 60 <= ttl_seconds <= 3600:
        raise ProviderLeaseError("provider_lease_ttl_invalid")
    timestamp = int(time.time()) if now is None else now
    record = LeaseRecord(name=name, owner=owner, expires_at=timestamp + ttl_seconds)
    stored = store.put_if_absent(record)
    return stored if stored is not None else record


def release_provider_lease(store: GitRemoteLeaseStore, record: LeaseRecord) -> None:
    store.delete_if_owner(record)
