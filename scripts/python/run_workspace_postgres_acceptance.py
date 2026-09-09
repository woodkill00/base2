#!/usr/bin/env python3
from __future__ import annotations

import os
import secrets
import subprocess
import time
from pathlib import Path

POSTGRES_IMAGE = (
    "mirror.gcr.io/library/postgres@sha256:"
    "075f7ba66bc9b3ce7d6b8b635208ff61cd7cf1a67d71ec530eec5d7ae0cbe571"
)


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    name = f"base2-workspace-postgres-{os.getpid()}"
    owner_password = secrets.token_urlsafe(32)
    api_runtime_password = secrets.token_urlsafe(32)
    runtime_password = secrets.token_urlsafe(32)
    worker_password = secrets.token_urlsafe(32)
    runtime_worker_password = secrets.token_urlsafe(32)
    email_worker_password = secrets.token_urlsafe(32)
    data_rights_worker_password = secrets.token_urlsafe(32)
    # The compose-built images track the current toolchain. The source under
    # test is still mounted read-only from the exact checkout below.
    django_image = os.getenv("WORKSPACE_ACCEPTANCE_DJANGO_IMAGE", "base2-local-django:latest")
    api_image = os.getenv("WORKSPACE_ACCEPTANCE_API_IMAGE", "base2-local-api:latest")
    started = False
    try:
        for image in (django_image, api_image):
            run(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL)
        run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                name,
                "--label",
                "base2.owner=feature-104-workspace-postgres",
                "-e",
                f"POSTGRES_PASSWORD={owner_password}",
                "-e",
                "POSTGRES_USER=base2",
                "-e",
                "POSTGRES_DB=base2",
                POSTGRES_IMAGE,
            ],
            stdout=subprocess.DEVNULL,
        )
        started = True
        consecutive_ready = 0
        for _ in range(40):
            ready = subprocess.run(
                [
                    "docker",
                    "exec",
                    name,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "base2",
                    "-d",
                    "base2",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if ready.returncode == 0:
                consecutive_ready += 1
                if consecutive_ready == 2:
                    break
            else:
                consecutive_ready = 0
            time.sleep(0.25)
        else:
            raise RuntimeError("workspace_postgres_not_ready")

        common = ["docker", "run", "--rm", "--network", f"container:{name}"]
        run(
            common
            + [
                "-v",
                f"{root}/postgres/bootstrap-workspace-role.sh:/bootstrap.sh:ro",
                "-e",
                "DB_HOST=127.0.0.1",
                "-e",
                "POSTGRES_USER=base2",
                "-e",
                f"POSTGRES_PASSWORD={owner_password}",
                "-e",
                "POSTGRES_DB=base2",
                "-e",
                "API_RUNTIME_DB_USER=base2_api_runtime",
                "-e",
                f"API_RUNTIME_DB_PASSWORD={api_runtime_password}",
                "-e",
                "WORKSPACE_DB_USER=base2_workspace_runtime",
                "-e",
                f"WORKSPACE_DB_PASSWORD={runtime_password}",
                "-e",
                "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
                "-e",
                f"WORKSPACE_WORKER_DB_PASSWORD={worker_password}",
                "-e",
                "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
                "-e",
                f"RUNTIME_WORKER_DB_PASSWORD={runtime_worker_password}",
                "-e",
                "EMAIL_WORKER_DB_USER=base2_email_worker",
                "-e",
                f"EMAIL_WORKER_DB_PASSWORD={email_worker_password}",
                "-e",
                "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
                "-e",
                f"DATA_RIGHTS_WORKER_DB_PASSWORD={data_rights_worker_password}",
                POSTGRES_IMAGE,
                "/bin/sh",
                "/bootstrap.sh",
            ],
            stdout=subprocess.DEVNULL,
        )
        api_migration = common + [
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{root}:/workspace:ro",
            "-w",
            "/workspace",
            "-e",
            "PYTHONPATH=/workspace",
            "-e",
            "DB_HOST=127.0.0.1",
            "-e",
            "DB_PORT=5432",
            "-e",
            "DB_NAME=base2",
            "-e",
            "DB_USER=base2",
            "-e",
            f"DB_PASSWORD={owner_password}",
            "--entrypoint",
            "python",
            api_image,
            "-m",
            "api.scripts.migrate",
        ]
        run(api_migration, stdout=subprocess.DEVNULL)
        django_migration = common + [
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{root}:/workspace:ro",
            "-w",
            "/workspace/django",
            "-e",
            "PYTHONPATH=/workspace/django",
            "-e",
            "DJANGO_SETTINGS_MODULE=project.settings.base",
            "-e",
            "DB_HOST=127.0.0.1",
            "-e",
            "DB_PORT=5432",
            "-e",
            "DB_NAME=base2",
            "-e",
            "DB_USER=base2",
            "-e",
            f"DB_PASSWORD={owner_password}",
            "-e",
            "WORKSPACE_DB_USER=base2_workspace_runtime",
            "-e",
            "API_RUNTIME_DB_USER=base2_api_runtime",
            "-e",
            "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
            "-e",
            "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
            "-e",
            "EMAIL_WORKER_DB_USER=base2_email_worker",
            "-e",
            "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
            "--entrypoint",
            "python",
            django_image,
            "manage.py",
            "migrate",
            "sitecontent",
        ]
        mixed_check = common + [
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{root}:/workspace:ro",
            "-w",
            "/workspace",
            "-e",
            "PYTHONPATH=/workspace",
            "-e",
            "DB_HOST=127.0.0.1",
            "-e",
            "DB_PORT=5432",
            "-e",
            "DB_NAME=base2",
            "-e",
            "DB_USER=base2",
            "-e",
            f"DB_PASSWORD={owner_password}",
            "--entrypoint",
            "python",
            api_image,
            "scripts/python/run_mixed_version_postgres_checks.py",
        ]
        run(django_migration + ["0025", "--noinput"], stdout=subprocess.DEVNULL)
        run(mixed_check + ["old"])
        run(django_migration + ["0026", "--noinput"], stdout=subprocess.DEVNULL)
        run(mixed_check + ["new"])
        run(
            common
            + [
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "-v",
                f"{root}:/workspace:ro",
                "-w",
                "/workspace/django",
                "-e",
                "PYTHONPATH=/workspace/django",
                "-e",
                "DJANGO_SETTINGS_MODULE=project.settings.base",
                "-e",
                "DB_HOST=127.0.0.1",
                "-e",
                "DB_PORT=5432",
                "-e",
                "DB_NAME=base2",
                "-e",
                "DB_USER=base2",
                "-e",
                f"DB_PASSWORD={owner_password}",
                "-e",
                "WORKSPACE_DB_USER=base2_workspace_runtime",
                "-e",
                "API_RUNTIME_DB_USER=base2_api_runtime",
                "-e",
                "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
                "-e",
                "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
                "-e",
                "EMAIL_WORKER_DB_USER=base2_email_worker",
                "-e",
                "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
                "--entrypoint",
                "python",
                django_image,
                "manage.py",
                "migrate",
                "--noinput",
            ],
            stdout=subprocess.DEVNULL,
        )
        run(
            common
            + [
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "-v",
                f"{root}:/workspace:ro",
                "-w",
                "/workspace",
                "-e",
                "PYTHONPATH=/workspace",
                "-e",
                "DB_HOST=127.0.0.1",
                "-e",
                "DB_PORT=5432",
                "-e",
                "DB_NAME=base2",
                "-e",
                "DB_USER=base2",
                "-e",
                f"DB_PASSWORD={owner_password}",
                "-e",
                "WORKSPACE_DB_USER=base2_workspace_runtime",
                "-e",
                f"WORKSPACE_DB_PASSWORD={runtime_password}",
                "-e",
                "API_RUNTIME_DB_USER=base2_api_runtime",
                "-e",
                f"API_RUNTIME_DB_PASSWORD={api_runtime_password}",
                "-e",
                "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
                "-e",
                f"WORKSPACE_WORKER_DB_PASSWORD={worker_password}",
                "-e",
                "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
                "-e",
                f"RUNTIME_WORKER_DB_PASSWORD={runtime_worker_password}",
                "-e",
                "EMAIL_WORKER_DB_USER=base2_email_worker",
                "-e",
                f"EMAIL_WORKER_DB_PASSWORD={email_worker_password}",
                "-e",
                "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
                "-e",
                f"DATA_RIGHTS_WORKER_DB_PASSWORD={data_rights_worker_password}",
                "--entrypoint",
                "python",
                api_image,
                "scripts/python/run_workspace_postgres_checks.py",
            ]
        )
        django_migration = common + [
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{root}:/workspace:ro",
            "-w",
            "/workspace/django",
            "-e",
            "PYTHONPATH=/workspace",
            "-e",
            "DJANGO_SETTINGS_MODULE=project.settings.base",
            "-e",
            "DB_HOST=127.0.0.1",
            "-e",
            "DB_PORT=5432",
            "-e",
            "DB_NAME=base2",
            "-e",
            "DB_USER=base2",
            "-e",
            f"DB_PASSWORD={owner_password}",
            "-e",
            "WORKSPACE_DB_USER=base2_workspace_runtime",
            "-e",
            "API_RUNTIME_DB_USER=base2_api_runtime",
            "-e",
            "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
            "-e",
            "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
            "-e",
            "EMAIL_WORKER_DB_USER=base2_email_worker",
            "-e",
            "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
            "--entrypoint",
            "python",
            django_image,
            "manage.py",
            "migrate",
            "sitecontent",
        ]
        role_check = common + [
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{root}:/workspace:ro",
            "-w",
            "/workspace",
            "-e",
            "PYTHONPATH=/workspace",
            "-e",
            "DB_HOST=127.0.0.1",
            "-e",
            "DB_PORT=5432",
            "-e",
            "DB_NAME=base2",
            "-e",
            "DB_USER=base2",
            "-e",
            f"DB_PASSWORD={owner_password}",
            "-e",
            "WORKSPACE_DB_USER=base2_workspace_runtime",
            "-e",
            "API_RUNTIME_DB_USER=base2_api_runtime",
            "-e",
            "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
            "-e",
            "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
            "-e",
            "EMAIL_WORKER_DB_USER=base2_email_worker",
            "-e",
            "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
            "--entrypoint",
            "python",
            api_image,
            "scripts/python/run_workspace_role_migration_checks.py",
        ]
        run(django_migration + ["0009", "--noinput"], stdout=subprocess.DEVNULL)
        run(role_check + ["reversed"])
        run(django_migration + ["0010", "--noinput"], stdout=subprocess.DEVNULL)
        run(role_check + ["forward"])
        media_check = common + [
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{root}:/workspace:ro",
            "-w",
            "/workspace",
            "-e",
            "PYTHONPATH=/workspace",
            "-e",
            "DB_HOST=127.0.0.1",
            "-e",
            "DB_PORT=5432",
            "-e",
            "DB_NAME=base2",
            "-e",
            "DB_USER=base2",
            "-e",
            f"DB_PASSWORD={owner_password}",
            "-e",
            "WORKSPACE_DB_USER=base2_workspace_runtime",
            "-e",
            f"WORKSPACE_DB_PASSWORD={runtime_password}",
            "-e",
            "API_RUNTIME_DB_USER=base2_api_runtime",
            "-e",
            f"API_RUNTIME_DB_PASSWORD={api_runtime_password}",
            "-e",
            "WORKSPACE_WORKER_DB_USER=base2_workspace_worker",
            "-e",
            f"WORKSPACE_WORKER_DB_PASSWORD={worker_password}",
            "-e",
            "RUNTIME_WORKER_DB_USER=base2_runtime_worker",
            "-e",
            f"RUNTIME_WORKER_DB_PASSWORD={runtime_worker_password}",
            "-e",
            "EMAIL_WORKER_DB_USER=base2_email_worker",
            "-e",
            f"EMAIL_WORKER_DB_PASSWORD={email_worker_password}",
            "-e",
            "DATA_RIGHTS_WORKER_DB_USER=base2_data_rights_worker",
            "-e",
            f"DATA_RIGHTS_WORKER_DB_PASSWORD={data_rights_worker_password}",
            "--entrypoint",
            "python",
            api_image,
            "scripts/python/run_media_postgres_checks.py",
        ]
        run(django_migration + ["0017", "--noinput"], stdout=subprocess.DEVNULL)
        run(media_check + ["forward"])
        run(django_migration + ["0010", "--noinput"], stdout=subprocess.DEVNULL)
        run(media_check + ["reversed"])
        run(django_migration + ["0017", "--noinput"], stdout=subprocess.DEVNULL)
        run(media_check + ["forward"])
    finally:
        if started:
            subprocess.run(
                ["docker", "rm", "--force", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    main()
