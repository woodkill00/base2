"""Restart-persistent, exact-lease workstation cleanup. Never runs a provider call."""

import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from digital_ocean.scripts.python.preview_lease_v2 import validate_lease


class ScheduleError(RuntimeError):
    pass


def _path(value, *, executable=False):
    path = Path(value)
    # Reject systemd substitutions, quoting, newlines and ambiguous path components.
    if (
        not path.is_absolute()
        or not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(path))
        or ".." in path.parts
        or any(p.is_symlink() for p in (path.parents if executable else (path, *path.parents)))
    ):
        raise ScheduleError("unsupported or linked schedule path")
    return str(path)


def render_units(lease, *, repo, python, state_root, credential_file):
    validate_lease(lease)
    repo, state_root, credential_file = map(_path, (repo, state_root, credential_file))
    python = _path(python, executable=True)  # venv interpreters are normal symlinks.
    expiry = datetime.fromisoformat(lease["expiresAt"].replace("Z", "+00:00")).astimezone(UTC)
    unit = "base2-preview-" + lease["runId"] + "-expiry"
    service = f"""[Unit]
Description=Exact-owned Base2 preview cleanup
StartLimitIntervalSec=600
StartLimitBurst=5

[Service]
Type=oneshot
WorkingDirectory={repo}
ExecStart={python} -m digital_ocean.scripts.python.full_preview_expire --state-root {state_root} --run-id {lease['runId']} --credential-file {credential_file} --stop-timer-on-success
Restart=on-failure
RestartSec=60
TimeoutStartSec=120
NoNewPrivileges=true
UMask=0077
"""
    timer = f"""[Unit]
Description=Bounded Base2 preview expiry (requires workstation online)

[Timer]
OnCalendar={expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC
Persistent=true
OnUnitInactiveSec=60
AccuracySec=1s
Unit={unit}.service

[Install]
WantedBy=timers.target
"""
    return {unit + ".service": service, unit + ".timer": timer}


def install_schedule(
    lease, *, repo, python, state_root, credential_file, unit_root=None, run=subprocess.run
):
    root = Path(unit_root or Path.home() / ".config/systemd/user")
    _path(root)
    units = render_units(
        lease, repo=repo, python=python, state_root=state_root, credential_file=credential_file
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, content in units.items():
        path = root / name
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file() or path.read_text() != content:
                raise ScheduleError("schedule already exists with different content")
        else:
            fd, temporary = tempfile.mkstemp(prefix=".preview-unit-", dir=root)
            try:
                with os.fdopen(fd, "w") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    timer = next(name for name in units if name.endswith(".timer"))
    for argv in (
        ["systemd-analyze", "--user", "verify", *[str(root / name) for name in units]],
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", timer],
        ["systemctl", "--user", "is-enabled", "--quiet", timer],
        ["systemctl", "--user", "is-active", "--quiet", timer],
    ):
        result = run(argv, capture_output=True, text=True, timeout=20, check=False)
        if result.returncode:
            raise ScheduleError("persistent expiry schedule could not be verified")
    return {
        "timer": timer,
        "persistent": True,
        "expiresAt": lease["expiresAt"],
        "requiresWorkstationOnline": True,
    }
