#!/usr/bin/env python3
"""Run an encrypted PostgreSQL dump and isolated restore with object reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.python.data_readiness import (  # noqa: E402
    provision_restore_root,
    reconcile_restore,
    recovery_strategy,
)
from scripts.python.recovery_assurance import (  # noqa: E402
    create_database_object_bundle,
    restore_stream_backup,
)

IMAGE = (
    "mirror.gcr.io/library/postgres@sha256:"
    "075f7ba66bc9b3ce7d6b8b635208ff61cd7cf1a67d71ec530eec5d7ae0cbe571"
)


def run(*parts: str, input_bytes: bytes | None = None, check: bool = True):
    return subprocess.run(parts, input=input_bytes, check=check, capture_output=True, timeout=30)


def component(count: int, value: bytes) -> dict:
    return {"count": count, "digest": hashlib.sha256(value).hexdigest(), "consistent": True}


def main() -> int:
    name = f"base2-recovery-{os.getpid()}"
    password = hashlib.sha256(os.urandom(32)).hexdigest()
    started = False
    try:
        run(
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "--label",
            "base2.owner=feature-106-recovery",
            "-e",
            f"POSTGRES_PASSWORD={password}",
            "-e",
            "POSTGRES_USER=base2",
            "-e",
            "POSTGRES_DB=base2",
            IMAGE,
        )
        started = True
        consecutive_ready = 0
        for _ in range(40):
            if (
                run(
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
                    check=False,
                ).returncode
                == 0
            ):
                consecutive_ready += 1
                if consecutive_ready == 2:
                    break
            else:
                consecutive_ready = 0
            time.sleep(0.25)
        else:
            raise RuntimeError("recovery_postgres_not_ready")
        sql = (
            "CREATE TABLE tenant_record(site_id text NOT NULL,value text NOT NULL);"
            "INSERT INTO tenant_record VALUES ('tenant-one','alpha'),('tenant-two','beta');"
        )
        run(
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={password}",
            name,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            "127.0.0.1",
            "-U",
            "base2",
            "-d",
            "base2",
            "-c",
            sql,
        )
        with tempfile.TemporaryDirectory(prefix="base2-recovery-") as temporary:
            root = Path(temporary)
            dump = root / "database.dump"
            dump.write_bytes(
                run(
                    "docker",
                    "exec",
                    "-e",
                    f"PGPASSWORD={password}",
                    name,
                    "pg_dump",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "base2",
                    "-d",
                    "base2",
                    "-Fc",
                ).stdout
            )
            objects = root / "objects"
            objects.mkdir()
            (objects / "tenant-one.bin").write_bytes(b"object-one")
            (objects / "tenant-two.bin").write_bytes(b"object-two")
            backup = root / "recovery.enc"
            key = hashlib.sha256(b"feature-106-disposable-recovery-key").digest()
            receipt = create_database_object_bundle(
                database_dump=dump,
                object_root=objects,
                output=backup,
                target_id="restore-drill-001",
                data_schema=29,
                key=key,
                key_ref="vaultwarden://base2/disposable-recovery-key",
                now=datetime.now(UTC),
            )
            dump.unlink()
            archive = root / "isolated/recovery.tar"
            provision_restore_root(root=archive.parent, target_class="isolated")
            restore_stream_backup(
                backup=backup,
                key=key,
                expected_target="restore-drill-001",
                expected_schema=29,
                output=archive,
            )
            with tarfile.open(archive, "r") as bundle:
                expected_members = [
                    "database.dump",
                    "objects.json",
                    "objects/tenant-one.bin",
                    "objects/tenant-two.bin",
                ]
                if sorted(bundle.getnames()) != expected_members:
                    raise RuntimeError("recovery_bundle_members_invalid")
                if any(not member.isfile() for member in bundle.getmembers()):
                    raise RuntimeError("recovery_bundle_member_unsafe")
                restored_dump = bundle.extractfile("database.dump").read()
                restored_objects = json.loads(bundle.extractfile("objects.json").read())
            target_count = run(
                "docker",
                "exec",
                "-e",
                f"PGPASSWORD={password}",
                name,
                "psql",
                "-At",
                "-h",
                "127.0.0.1",
                "-U",
                "base2",
                "-d",
                "postgres",
                "-c",
                "SELECT count(*) FROM pg_database WHERE datname='restore_drill_001'",
            ).stdout.strip()
            if target_count != b"0":
                raise RuntimeError("recovery_target_not_empty")
            run(
                "docker",
                "exec",
                "-e",
                f"PGPASSWORD={password}",
                name,
                "createdb",
                "-h",
                "127.0.0.1",
                "-U",
                "base2",
                "restore_drill_001",
            )
            target_count = run(
                "docker",
                "exec",
                "-e",
                f"PGPASSWORD={password}",
                name,
                "psql",
                "-At",
                "-h",
                "127.0.0.1",
                "-U",
                "base2",
                "-d",
                "postgres",
                "-c",
                "SELECT count(*) FROM pg_database WHERE datname='restore_drill_001'",
            ).stdout.strip()
            if target_count != b"1":
                raise RuntimeError("recovery_target_creation_unverified")
            run(
                "docker",
                "exec",
                "-i",
                "-e",
                f"PGPASSWORD={password}",
                name,
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "-h",
                "127.0.0.1",
                "-U",
                "base2",
                "-d",
                "restore_drill_001",
                input_bytes=restored_dump,
            )
            original = run(
                "docker",
                "exec",
                "-e",
                f"PGPASSWORD={password}",
                name,
                "psql",
                "-At",
                "-h",
                "127.0.0.1",
                "-U",
                "base2",
                "-d",
                "base2",
                "-c",
                "SELECT site_id||':'||value FROM tenant_record ORDER BY site_id",
            ).stdout
            restored = run(
                "docker",
                "exec",
                "-e",
                f"PGPASSWORD={password}",
                name,
                "psql",
                "-At",
                "-h",
                "127.0.0.1",
                "-U",
                "base2",
                "-d",
                "restore_drill_001",
                "-c",
                "SELECT site_id||':'||value FROM tenant_record ORDER BY site_id",
            ).stdout
            if original != restored or restored_objects["digest"] != receipt["objectDigest"]:
                raise RuntimeError("recovery_reconciliation_failed")
            components = {
                "relational": component(2, restored),
                "objects": component(
                    restored_objects["count"], restored_objects["digest"].encode()
                ),
                "search": component(0, b"disabled"),
                "configuration": component(1, b"schema-27"),
                "tenants": component(2, b"tenant-one\ntenant-two"),
                "audit": component(0, b"empty-audit"),
            }
            reconciliation = reconcile_restore(components)
            strategy = recovery_strategy([])
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "encrypted": receipt["encrypted"],
                        "restoreTarget": "restore-drill-001",
                        "reconciliation": reconciliation["digest"],
                        "recoveryMode": strategy["mode"],
                        "plaintextRetained": False,
                    },
                    sort_keys=True,
                )
            )
        return 0
    finally:
        if started:
            run("docker", "rm", "-f", name, check=False)


if __name__ == "__main__":
    raise SystemExit(main())
