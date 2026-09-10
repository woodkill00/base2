from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


@pytest.mark.parametrize("down_exit", [0, 7])
def test_embedded_fresh_target_rollback_restores_source_and_removes_runtime(
    tmp_path: Path, down_exit: int
):
    source = (ROOT / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    function = source.split("function Invoke-RollbackOnFailureIfEnabled", 1)[1].split(
        "function ", 1
    )[0]
    match = re.search(r"\$remote = @'\n(.*?)\n'@", function, re.DOTALL)
    assert match is not None

    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init", "-q"], cwd=repo)
    run(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    (repo / "tracked.txt").write_text("prior\n", encoding="utf-8")
    run(["git", "add", "tracked.txt"], cwd=repo)
    run(["git", "commit", "-qm", "prior"], cwd=repo)
    prior = run(["git", "rev-parse", "HEAD"], cwd=repo)
    (repo / "tracked.txt").write_text("candidate\n", encoding="utf-8")
    run(["git", "commit", "-qam", "candidate"], cwd=repo)
    (repo / ".env").write_text("TRANSFERRED_SECRET=canary\n", encoding="utf-8")

    state = tmp_path / "rollback-private"
    logs = tmp_path / "logs"
    (logs / "build").mkdir(parents=True)
    state.mkdir()
    (state / "pre-deploy-head.txt").write_text(f"{prior}\n", encoding="utf-8")
    (state / "pre-deploy-epoch.txt").write_text("", encoding="utf-8")
    (state / "deployment-kind.txt").write_text("fresh\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{docker_log}'\n"
        f'case "$*" in *" down "*) exit {down_exit};; esac\n'
        "exit 0\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)

    script = (
        match.group(1)
        .replace("__REMOTE_APP_DIR__", str(repo))
        .replace("/root/base2-rollback-private", str(state))
        .replace("/root/logs", str(logs))
    )
    env = dict(os.environ)
    env["PATH"] = f'{bin_dir}:{env["PATH"]}'
    env["COMPOSE_PROJECT_NAME"] = "generated-custom-project"
    if down_exit:
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.run(
                ["bash", "-eu", "-c", script],
                cwd=repo,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
        assert (repo / ".env").exists()
        assert state.exists()
        return
    completed = subprocess.run(
        ["bash", "-eu", "-c", script],
        cwd=repo,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Fresh-target rollback completed" in completed.stdout
    assert run(["git", "rev-parse", "HEAD"], cwd=repo) == prior
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "prior\n"
    assert not (repo / ".env").exists()
    assert not state.exists()
    assert "--profile celery down --remove-orphans" in docker_log.read_text(encoding="utf-8")
