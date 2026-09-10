#!/usr/bin/env python3
"""Exact-owner remote Git compare-and-swap lease for paid provisioning.

DigitalOcean Spaces does not document conditional object creation or deletion,
so a Spaces object cannot safely serialize paid resource creation. This store
uses atomic Git ref creation and force-with-lease deletion against the already
configured source remote. Conflict, crash, drift, and stale ownership all fail
closed before another paid resource can be created.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit


class ProviderLeaseError(RuntimeError):
    pass


def _trusted_git_executable() -> str:
    candidates = (
        [Path(r"C:\Program Files\Git\cmd\git.exe")]
        if os.name == "nt"
        else [Path("/usr/bin/git")]
    )
    for candidate in candidates:
        try:
            if candidate.is_symlink():
                continue
            resolved = candidate.resolve(strict=True)
            if resolved.is_file() and os.access(resolved, os.X_OK):
                return str(resolved)
        except OSError:
            continue
    raise ProviderLeaseError("provider_lease_git_unavailable")


GIT_EXECUTABLE = _trusted_git_executable()


def _trusted_windows_directory() -> Path:
    """Read the real Windows directory from the kernel, never the environment."""

    buffer = ctypes.create_unicode_buffer(32768)
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        length = kernel32.GetWindowsDirectoryW(buffer, len(buffer))
    except (AttributeError, OSError) as exc:
        raise ProviderLeaseError("provider_lease_windows_directory_invalid") from exc
    if length < 1 or length >= len(buffer):
        raise ProviderLeaseError("provider_lease_windows_directory_invalid")
    candidate = Path(buffer.value)
    try:
        if not candidate.is_absolute() or candidate.is_symlink():
            raise ProviderLeaseError("provider_lease_windows_directory_invalid")
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ProviderLeaseError("provider_lease_windows_directory_invalid") from exc
    if not resolved.is_dir():
        raise ProviderLeaseError("provider_lease_windows_directory_invalid")
    return resolved


def _windows_broker_acl_restrictive(path: Path) -> bool:
    """Verify owner and writable ancestry using SID-based Windows ACL checks."""

    try:
        windows_directory = _trusted_windows_directory()
        powershell = (
            windows_directory / r"System32\WindowsPowerShell\v1.0\powershell.exe"
        )
        if powershell.is_symlink():
            return False
        powershell = powershell.resolve(strict=True)
        if not powershell.is_file() or not powershell.is_relative_to(windows_directory):
            return False
    except (OSError, ProviderLeaseError):
        return False
    script = r"""
$ErrorActionPreference = 'Stop'
$me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$safe = @($me, 'S-1-5-18', 'S-1-5-32-544')
$item = Get-Item -LiteralPath $env:BASE2_BROKER_PATH -Force
$first = $true
while ($null -ne $item) {
  $acl = Get-Acl -LiteralPath $item.FullName
  if ($first) {
    $owner = $acl.Owner
    try { $owner = ([Security.Principal.NTAccount]$owner).Translate([Security.Principal.SecurityIdentifier]).Value } catch {}
    if ($owner -ne $me) { exit 4 }
    $first = $false
  }
  foreach ($ace in $acl.Access) {
    if ($ace.AccessControlType -ne 'Allow') { continue }
    if ($ace.PropagationFlags.ToString().Contains('InheritOnly')) { continue }
    $sid = $ace.IdentityReference.Value
    try { $sid = $ace.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value } catch { exit 5 }
    $writeMask = 852310
    if ((([int64]$ace.FileSystemRights -band $writeMask) -ne 0) -and ($safe -notcontains $sid)) { exit 6 }
  }
  $item = $item.Parent
}
exit 0
"""
    environment = {
        "BASE2_BROKER_PATH": str(path),
        "SYSTEMROOT": str(windows_directory),
        "WINDIR": str(windows_directory),
    }
    try:
        result = subprocess.run(
            [str(powershell), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _credential_broker(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute() or candidate.is_symlink():
        raise ProviderLeaseError("provider_lease_credential_broker_invalid")
    try:
        resolved = candidate.resolve(strict=True)
        metadata = resolved.stat()
    except OSError as exc:
        raise ProviderLeaseError("provider_lease_credential_broker_invalid") from exc
    if not resolved.is_file() or metadata.st_size < 1 or metadata.st_size > 65536:
        raise ProviderLeaseError("provider_lease_credential_broker_invalid")
    if os.name == "nt":
        if not _windows_broker_acl_restrictive(resolved):
            raise ProviderLeaseError("provider_lease_credential_broker_invalid")
    elif metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise ProviderLeaseError("provider_lease_credential_broker_invalid")
    if not os.access(resolved, os.X_OK):
        raise ProviderLeaseError("provider_lease_credential_broker_invalid")
    return resolved


def _validate_private_path(path: Path) -> None:
    if os.name == "nt":
        if not _windows_broker_acl_restrictive(path):
            raise ProviderLeaseError("provider_lease_private_temp_invalid")
        return
    try:
        metadata = path.stat()
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise ProviderLeaseError("provider_lease_private_temp_invalid")
        current = path.parent
        while True:
            parent_metadata = current.stat()
            unsafe_write = parent_metadata.st_mode & 0o022
            if unsafe_write and not parent_metadata.st_mode & stat.S_ISVTX:
                raise ProviderLeaseError("provider_lease_private_temp_invalid")
            if parent_metadata.st_uid not in {0, os.getuid()}:
                raise ProviderLeaseError("provider_lease_private_temp_invalid")
            if current.parent == current:
                break
            current = current.parent
    except OSError as exc:
        raise ProviderLeaseError("provider_lease_private_temp_invalid") from exc


@contextmanager
def _private_temp_directory(anchor: Path, prefix: str):
    """Create validated private storage without consulting ambient temp paths."""

    try:
        resolved_anchor = anchor.resolve(strict=True)
        git_metadata = resolved_anchor / ".git"
        private_parent = (
            git_metadata / "base2-provider-lease-private"
            if git_metadata.is_dir() and not git_metadata.is_symlink()
            else resolved_anchor / ".base2-provider-lease-private"
        )
        private_parent.mkdir(mode=0o700, exist_ok=True)
        private_parent.chmod(0o700)
        _validate_private_path(private_parent)
        with tempfile.TemporaryDirectory(prefix=prefix, dir=private_parent) as raw_root:
            root = Path(raw_root).resolve(strict=True)
            root.chmod(0o700)
            _validate_private_path(root)
            yield root
    except OSError as exc:
        raise ProviderLeaseError("provider_lease_private_temp_invalid") from exc


def _network_remote_identity(value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme == "https":
        if (
            parsed.username
            or parsed.password
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
    credential_broker: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_SSL_NO_VERIFY": "false",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": str(Path(GIT_EXECUTABLE).parent),
    }
    if credential_broker is not None:
        environment["GIT_ASKPASS"] = str(credential_broker)
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
        with _private_temp_directory(cwd, "git-scratch-") as private_temp:
            if os.name == "nt":
                windows_directory = _trusted_windows_directory()
                environment.update(
                    {
                        "SYSTEMROOT": str(windows_directory),
                        "TEMP": str(private_temp),
                        "TMP": str(private_temp),
                        "WINDIR": str(windows_directory),
                    }
                )
            else:
                environment["TMPDIR"] = str(private_temp)
            return subprocess.run(
                [GIT_EXECUTABLE, *command],
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

    def __init__(
        self,
        *,
        remote: str = "origin",
        repository: Path | None = None,
        credential_broker: Path | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", remote):
            raise ProviderLeaseError("provider_lease_remote_invalid")
        self.remote = remote
        self.repository = (repository or Path.cwd()).resolve()
        self.credential_broker = credential_broker
        push_url = _git(
            ["config", "--local", "--get", f"remote.{remote}.pushurl"],
            cwd=self.repository,
        )
        configured = push_url
        if push_url.returncode:
            configured = _git(
                ["config", "--local", "--get", f"remote.{remote}.url"],
                cwd=self.repository,
            )
        self.remote_url = configured.stdout.strip()
        if configured.returncode or not self.remote_url or "\n" in self.remote_url:
            raise ProviderLeaseError("provider_lease_remote_unavailable")
        self.remote_identity = _network_remote_identity(self.remote_url)
        scp_transport = re.fullmatch(
            r"(?:[A-Za-z0-9._-]+@)?[A-Za-z0-9.-]+:[^\s]+", self.remote_url
        )
        if (urlsplit(self.remote_url).scheme or scp_transport) and self.remote_identity is None:
            raise ProviderLeaseError("provider_lease_remote_unsafe")

    @classmethod
    def from_environment(cls) -> GitRemoteLeaseStore:
        remote = os.environ.get("DO_PROVISION_LEASE_GIT_REMOTE", "").strip()
        if not remote:
            raise ProviderLeaseError("provider_lease_remote_required")
        broker_raw = os.environ.get("DO_PROVISION_LEASE_GIT_ASKPASS", "").strip()
        if not broker_raw:
            raise ProviderLeaseError("provider_lease_credential_broker_required")
        store = cls(remote=remote, credential_broker=_credential_broker(broker_raw))
        if store.remote_identity is None:
            raise ProviderLeaseError("provider_lease_remote_not_shared")
        source = _git(
            ["config", "--local", "--get", "remote.origin.pushurl"],
            cwd=store.repository,
        )
        if source.returncode:
            source = _git(
                ["config", "--local", "--get", "remote.origin.url"],
                cwd=store.repository,
            )
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
        with _private_temp_directory(
            self.repository, "lease-construction-"
        ) as root:
            if _git(
                ["init", "--quiet"], cwd=root, credential_broker=self.credential_broker
            ).returncode:
                raise ProviderLeaseError("provider_lease_local_init_failed")
            blob = _git(
                ["hash-object", "-w", "--stdin"],
                cwd=root,
                stdin=record.payload().decode(),
                credential_broker=self.credential_broker,
            )
            if blob.returncode or not re.fullmatch(r"[0-9a-f]{40,64}\n?", blob.stdout):
                raise ProviderLeaseError("provider_lease_local_object_failed")
            tree = _git(
                ["mktree"],
                cwd=root,
                stdin=f"100644 blob {blob.stdout.strip()}\tlease.json\n",
                credential_broker=self.credential_broker,
            )
            if tree.returncode or not re.fullmatch(r"[0-9a-f]{40,64}\n?", tree.stdout):
                raise ProviderLeaseError("provider_lease_local_object_failed")
            commit = _git(
                ["commit-tree", tree.stdout.strip(), "-m", "base2 provider lease"],
                cwd=root,
                identity=True,
                credential_broker=self.credential_broker,
            )
            revision = commit.stdout.strip()
            if commit.returncode or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
                raise ProviderLeaseError("provider_lease_local_object_failed")
            pushed = _git(
                ["push", "--porcelain", self.remote_url, f"{revision}:{self._ref(record.name)}"],
                cwd=root,
                credential_broker=self.credential_broker,
            )
            if pushed.returncode:
                raise ProviderLeaseError("provider_provision_lease_unavailable")
            return replace(record, revision=revision)

    def delete_if_owner(self, record: LeaseRecord) -> None:
        if not re.fullmatch(r"[0-9a-f]{40,64}", record.revision):
            raise ProviderLeaseError("provider_provision_lease_owner_mismatch")
        with _private_temp_directory(
            self.repository, "lease-release-"
        ) as root:
            if _git(
                ["init", "--quiet"], cwd=root, credential_broker=self.credential_broker
            ).returncode:
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
                credential_broker=self.credential_broker,
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
