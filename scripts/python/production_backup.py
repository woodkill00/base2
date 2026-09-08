#!/usr/bin/env python3
"""Production backup, retention, verification, and isolated-restore entrypoint.

Credentials remain in owner-only libpq/key files. Database URLs and secret
values are never accepted on the command line or written to receipts.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import fcntl
import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from scripts.python.data_readiness import provision_restore_root
from scripts.python.recovery_assurance import (
    RecoveryDenied,
    create_database_object_bundle,
    restore_stream_backup,
)

SAFE_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
KEY_REF = re.compile(r"^vaultwarden://[A-Za-z0-9][A-Za-z0-9._/-]{2,254}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CONFIG_KEYS = {
    "schemaVersion",
    "targetId",
    "dataSchema",
    "pgServiceFile",
    "pgService",
    "objectRoot",
    "objectStorageKeyFile",
    "backupRoot",
    "receiptRoot",
    "encryptionKeyFile",
    "keyRef",
    "retentionDays",
    "maximumBackups",
    "operationsReceiptRoot",
    "operationsReceiptKeyFile",
    "sourceCommit",
}


class ProductionBackupError(ValueError):
    pass


def _private_file(path: Path, *, maximum_bytes: int) -> bytes:
    if not path.is_absolute() or path.is_symlink():
        raise ProductionBackupError("backup:private_file_invalid")
    try:
        metadata = path.stat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_mode & 0o077
            or metadata.st_size > maximum_bytes
        ):
            raise ProductionBackupError("backup:private_file_invalid")
        return path.read_bytes()
    except OSError as exc:
        raise ProductionBackupError("backup:private_file_invalid") from exc


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_private_file(path, maximum_bytes=32_768))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProductionBackupError("backup:configuration_invalid") from exc
    if not isinstance(value, dict) or set(value) != CONFIG_KEYS:
        raise ProductionBackupError("backup:configuration_invalid")
    absolute = (
        "pgServiceFile",
        "objectRoot",
        "objectStorageKeyFile",
        "backupRoot",
        "receiptRoot",
        "encryptionKeyFile",
        "operationsReceiptRoot",
        "operationsReceiptKeyFile",
    )
    if (
        value["schemaVersion"] != 1
        or not SAFE_ID.fullmatch(str(value["targetId"]))
        or not SAFE_ID.fullmatch(str(value["pgService"]))
        or not KEY_REF.fullmatch(str(value["keyRef"]))
        or type(value["dataSchema"]) is not int
        or value["dataSchema"] < 1
        or type(value["retentionDays"]) is not int
        or not 1 <= value["retentionDays"] <= 365
        or type(value["maximumBackups"]) is not int
        or not 2 <= value["maximumBackups"] <= 366
        or not re.fullmatch(r"[0-9a-f]{40}", str(value["sourceCommit"]))
        or any(not str(value[name]).startswith("/") for name in absolute)
    ):
        raise ProductionBackupError("backup:configuration_invalid")
    _private_file(Path(value["pgServiceFile"]), maximum_bytes=16_384)
    key_file = Path(value["encryptionKeyFile"])
    encoded = _private_file(key_file, maximum_bytes=256).strip()
    try:
        key = base64.b64decode(encoded + b"=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ProductionBackupError("backup:key_invalid") from exc
    if len(key) != 32:
        raise ProductionBackupError("backup:key_invalid")
    value["_key"] = key
    encoded_object_key = _private_file(
        Path(value["objectStorageKeyFile"]), maximum_bytes=256
    ).strip()
    try:
        object_key = base64.b64decode(
            encoded_object_key + b"=" * (-len(encoded_object_key) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise ProductionBackupError("backup:object_key_invalid") from exc
    if len(object_key) != 32:
        raise ProductionBackupError("backup:object_key_invalid")
    value["_object_key"] = object_key
    encoded_operations_key = _private_file(
        Path(value["operationsReceiptKeyFile"]), maximum_bytes=256
    ).strip()
    try:
        operations_key = base64.b64decode(
            encoded_operations_key + b"=" * (-len(encoded_operations_key) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise ProductionBackupError("backup:operations_key_invalid") from exc
    if len(operations_key) < 32:
        raise ProductionBackupError("backup:operations_key_invalid")
    value["_operations_key"] = operations_key
    return value


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


OBJECT_REFERENCE_SQL = """SELECT kind || ':' || site_id || ':' || object_key || ':' || digest
 FROM (
   SELECT 'asset' kind,site_id,storage_key object_key,sha256 digest
     FROM sitecontent_mediaasset
   UNION ALL
   SELECT 'variant',asset.site_id,variant.storage_key,variant.sha256
     FROM sitecontent_mediavariant variant
     JOIN sitecontent_mediaasset asset ON asset.id=variant.asset_id
   UNION ALL
   SELECT 'object-version',site_id,storage_key,sha256
     FROM sitecontent_mediaobjectversion
   UNION ALL
   SELECT 'upload-part',site_id,storage_key,sha256
     FROM sitecontent_mediauploadpart
   UNION ALL
   SELECT 'import',site_id,source_object_key,source_sha256
     FROM sitecontent_importjob WHERE source_object_key<>''
   UNION ALL
   SELECT 'export',site_id,encrypted_object_key,output_sha256
     FROM sitecontent_exportjob WHERE encrypted_object_key<>''
 ) object_refs ORDER BY kind,site_id,object_key,digest"""


def _verify_object_references(raw: str, *, object_root: Path, key: bytes) -> None:
    root = object_root.resolve(strict=True)
    expected_objects: dict[str, str] = {}
    for line in raw.splitlines():
        value = line.strip()
        if not value:
            continue
        try:
            _kind, tenant_id, object_key, expected = value.split(":", 3)
        except ValueError as exc:
            raise ProductionBackupError("backup:object_reference_ledger_invalid") from exc
        candidate = (root / object_key).resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ProductionBackupError("backup:object_reference_invalid") from exc
        if (
            not object_key
            or not object_key.split("/")[1:2] == [tenant_id]
            or candidate.is_symlink()
            or not SHA256.fullmatch(expected)
        ):
            raise ProductionBackupError("backup:object_reference_invalid")
        previous = expected_objects.setdefault(object_key, expected)
        if previous != expected:
            raise ProductionBackupError("backup:object_reference_conflict")
        try:
            envelope = candidate.read_bytes()
        except OSError as exc:
            raise ProductionBackupError("backup:referenced_object_missing") from exc
        if len(envelope) < 31 or not envelope.startswith(b"CW1"):
            raise ProductionBackupError("backup:referenced_object_invalid")
        try:
            content = AESGCM(key).decrypt(envelope[3:15], envelope[15:], object_key.encode())
        except (InvalidTag, ValueError) as exc:
            raise ProductionBackupError("backup:referenced_object_invalid") from exc
        if hashlib.sha256(content).hexdigest() != expected:
            raise ProductionBackupError("backup:referenced_object_digest_mismatch")
    actual_objects: set[str] = set()
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise ProductionBackupError("backup:object_symlink_denied")
        if candidate.is_file():
            actual_objects.add(candidate.relative_to(root).as_posix())
    if actual_objects != set(expected_objects):
        raise ProductionBackupError("backup:object_inventory_mismatch")


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _write_operations_receipt(
    config: dict[str, Any], *, kind: str, artifact_digest: str, now: datetime
) -> None:
    receipt = {
        "schemaVersion": 1,
        "kind": kind,
        "status": "passed",
        "sourceCommit": config["sourceCommit"],
        "artifactDigest": artifact_digest,
        "observedAt": now.astimezone(UTC).isoformat(),
        "expiresAt": (now.astimezone(UTC) + timedelta(hours=36)).isoformat(),
    }
    receipt["digest"] = hmac.new(
        config["_operations_key"], _canonical(receipt), hashlib.sha256
    ).hexdigest()
    _write_private_json(Path(config["operationsReceiptRoot"]) / f"{kind}.json", receipt)


def _receipt_body(receipt: dict[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in receipt.items() if name != "receiptHmac"}


def _sign(receipt: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical(_receipt_body(receipt)), hashlib.sha256).hexdigest()


def verify_receipt(receipt: dict[str, Any], *, key: bytes, backup_root: Path) -> Path:
    required = {
        "schemaVersion",
        "targetId",
        "status",
        "createdAt",
        "retentionExpiresAt",
        "backupFile",
        "backupSha256",
        "backupSize",
        "databaseDumpSha256",
        "objectCount",
        "objectDigest",
        "encrypted",
        "keyRef",
        "receiptHmac",
    }
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt["schemaVersion"] != 1
        or receipt["status"] != "complete"
        or receipt["encrypted"] is not True
        or not SHA256.fullmatch(str(receipt["backupSha256"]))
        or not SHA256.fullmatch(str(receipt["databaseDumpSha256"]))
        or not SHA256.fullmatch(str(receipt["objectDigest"]))
        or not hmac.compare_digest(str(receipt["receiptHmac"]), _sign(receipt, key))
    ):
        raise ProductionBackupError("backup:receipt_invalid")
    candidate = backup_root / str(receipt["backupFile"])
    try:
        candidate.resolve(strict=True).relative_to(backup_root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ProductionBackupError("backup:receipt_invalid") from exc
    if candidate.is_symlink() or not candidate.is_file():
        raise ProductionBackupError("backup:unavailable")
    digest = hashlib.sha256()
    with candidate.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    if (
        digest.hexdigest() != receipt["backupSha256"]
        or candidate.stat().st_size != receipt["backupSize"]
    ):
        raise ProductionBackupError("backup:integrity_failed")
    return candidate


def create_production_backup(
    config: dict[str, Any],
    *,
    now: datetime | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict[str, Any]:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    stamp = current.strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path(config["backupRoot"])
    receipt_root = Path(config["receiptRoot"])
    object_root = Path(config["objectRoot"])
    for root in (backup_root, receipt_root):
        if root.is_symlink():
            raise ProductionBackupError("backup:root_invalid")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
    if object_root.is_symlink() or not object_root.is_dir():
        raise ProductionBackupError("backup:object_root_invalid")
    lock_path = receipt_root / ".production-backup.lock"
    with lock_path.open("a+b") as lock:
        os.chmod(lock_path, 0o600)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProductionBackupError("backup:already_running") from exc
        with tempfile.TemporaryDirectory(prefix="base2-production-backup-") as temporary:
            dump = Path(temporary) / "database.dump"
            staged_objects = Path(temporary) / "objects"
            environment = {
                "PATH": os.environ.get("PATH", ""),
                "PGSERVICEFILE": str(config["pgServiceFile"]),
            }
            reference_command = [
                "psql",
                f"service={config['pgService']}",
                "--tuples-only",
                "--no-align",
                "--command",
                OBJECT_REFERENCE_SQL,
            ]
            before_references = runner(
                reference_command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if before_references.returncode != 0:
                raise ProductionBackupError("backup:object_reference_ledger_invalid")
            ledger = runner(
                [
                    "psql",
                    f"service={config['pgService']}",
                    "--tuples-only",
                    "--no-align",
                    "--command",
                    "SELECT COALESCE(MAX((regexp_match(name, '^[0-9]+'))[1]::int),0) "
                    "FROM django_migrations WHERE app='sitecontent'",
                ],
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            try:
                live_schema = int((ledger.stdout or "").strip())
            except ValueError as exc:
                raise ProductionBackupError("backup:schema_ledger_invalid") from exc
            if ledger.returncode != 0 or live_schema != config["dataSchema"]:
                raise ProductionBackupError("backup:schema_mismatch")
            completed = runner(
                [
                    "pg_dump",
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    str(dump),
                    f"service={config['pgService']}",
                ],
                env=environment,
                capture_output=True,
                text=True,
                timeout=3600,
                check=False,
            )
            if completed.returncode != 0 or not dump.is_file() or dump.stat().st_size < 1:
                raise ProductionBackupError("backup:pg_dump_failed")
            dump_digest = _sha256_file(dump)
            # Read the live object tree exactly once into a private temporary
            # boundary. The archive never rereads mutable production paths.
            # The reference-ledger comparison below proves no database-visible
            # object identity changed around this stable copy.
            try:
                # Preserve links in the private staging tree so the bundle
                # inventory rejects them. Following a live-tree symlink here
                # could otherwise archive data outside the owned object root.
                shutil.copytree(object_root, staged_objects, symlinks=True)
            except (OSError, shutil.Error) as exc:
                raise ProductionBackupError("backup:object_snapshot_failed") from exc
            _verify_object_references(
                before_references.stdout,
                object_root=staged_objects,
                key=config["_object_key"],
            )
            output = backup_root / f"{config['targetId']}-{stamp}.tar.enc"
            try:
                bundle = create_database_object_bundle(
                    database_dump=dump,
                    object_root=staged_objects,
                    output=output,
                    target_id=config["targetId"],
                    data_schema=config["dataSchema"],
                    key=config["_key"],
                    key_ref=config["keyRef"],
                    now=current,
                )
            except RecoveryDenied as exc:
                raise ProductionBackupError(str(exc)) from exc
            after_references = runner(
                reference_command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if (
                after_references.returncode != 0
                or before_references.stdout != after_references.stdout
            ):
                output.unlink(missing_ok=True)
                raise ProductionBackupError("backup:cross_surface_snapshot_changed")
        receipt = {
            "schemaVersion": 1,
            "targetId": config["targetId"],
            "status": "complete",
            "createdAt": current.isoformat().replace("+00:00", "Z"),
            "retentionExpiresAt": (current + timedelta(days=config["retentionDays"]))
            .isoformat()
            .replace("+00:00", "Z"),
            "backupFile": output.name,
            "backupSha256": bundle["sha256"],
            "backupSize": bundle["size"],
            "databaseDumpSha256": dump_digest,
            "objectCount": bundle["objectCount"],
            "objectDigest": bundle["objectDigest"],
            "encrypted": True,
            "keyRef": config["keyRef"],
        }
        receipt["receiptHmac"] = _sign(receipt, config["_key"])
        _write_private_json(receipt_root / f"{config['targetId']}-{stamp}.json", receipt)
        _write_operations_receipt(
            config,
            kind="backup",
            artifact_digest=bundle["sha256"],
            now=current,
        )
        return receipt


def prune_owned_backups(config: dict[str, Any], *, now: datetime | None = None) -> dict[str, int]:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    receipt_root, backup_root = Path(config["receiptRoot"]), Path(config["backupRoot"])
    quarantine = backup_root / "quarantine"

    def admit_quarantine(size: int) -> None:
        existing = [path for path in quarantine.iterdir()] if quarantine.exists() else []
        bytes_used = sum(path.stat().st_size for path in existing if path.is_file())
        maximum_items = max(10, int(config["maximumBackups"]) * 2)
        if len(existing) >= maximum_items or bytes_used + size > 1024 * 1024 * 1024:
            raise ProductionBackupError("backup:quarantine_capacity_exceeded")

    valid: list[tuple[datetime, Path, Path]] = []
    rejected = 0
    for path in sorted(receipt_root.glob(f"{config['targetId']}-*.json")):
        if path.is_symlink():
            rejected += 1
            continue
        try:
            receipt = json.loads(_private_file(path, maximum_bytes=32_768))
            backup = verify_receipt(receipt, key=config["_key"], backup_root=backup_root)
            created = datetime.fromisoformat(str(receipt["createdAt"]).replace("Z", "+00:00"))
            expiry = datetime.fromisoformat(
                str(receipt["retentionExpiresAt"]).replace("Z", "+00:00")
            )
        except (ProductionBackupError, ValueError, json.JSONDecodeError):
            admit_quarantine(path.stat().st_size)
            quarantine.mkdir(mode=0o700, parents=True, exist_ok=True)
            quarantine.chmod(0o700)
            suffix = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            os.replace(path, quarantine / f"rejected-receipt-{suffix}.json")
            rejected += 1
            continue
        valid.append((max(created, expiry if expiry <= current else created), path, backup))
    referenced = {backup.resolve() for _date, _receipt, backup in valid}
    orphaned = 0
    for backup in sorted(backup_root.glob(f"{config['targetId']}-*.tar.enc")):
        if backup.is_symlink() or not backup.is_file() or backup.resolve() in referenced:
            continue
        admit_quarantine(backup.stat().st_size)
        quarantine.mkdir(mode=0o700, parents=True, exist_ok=True)
        quarantine.chmod(0o700)
        suffix = hashlib.sha256(backup.read_bytes()).hexdigest()[:12]
        os.replace(backup, quarantine / f"orphan-backup-{suffix}.tar.enc")
        orphaned += 1
    valid.sort(key=lambda item: item[0], reverse=True)
    removed = 0
    for index, (_date, receipt_path, backup_path) in enumerate(valid):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        expiry = datetime.fromisoformat(str(receipt["retentionExpiresAt"]).replace("Z", "+00:00"))
        if expiry > current and index < config["maximumBackups"]:
            continue
        backup_path.unlink()
        receipt_path.unlink()
        removed += 1
    return {
        "verified": len(valid),
        "removed": removed,
        "rejected": rejected,
        "orphaned": orphaned,
    }


def isolated_restore(
    config: dict[str, Any], *, receipt_path: Path, restore_root: Path
) -> dict[str, Any]:
    """Decrypt one verified backup into a newly provisioned isolated filesystem root."""
    receipt = json.loads(_private_file(receipt_path, maximum_bytes=32_768))
    backup = verify_receipt(receipt, key=config["_key"], backup_root=Path(config["backupRoot"]))
    provision_restore_root(root=restore_root, target_class="isolated")
    archive = restore_root / "recovery.tar"
    restored = restore_stream_backup(
        backup=backup,
        key=config["_key"],
        expected_target=config["targetId"],
        expected_schema=config["dataSchema"],
        output=archive,
        target_class="isolated",
    )
    payload = restore_root / "payload"
    payload.mkdir(mode=0o700)
    with tarfile.open(archive, "r:") as bundle:
        members = bundle.getmembers()
        if any(
            member.issym()
            or member.islnk()
            or member.name.startswith("/")
            or ".." in Path(member.name).parts
            or not (
                member.name in {"database.dump", "objects.json"}
                or member.name.startswith("objects/")
            )
            for member in members
        ):
            raise ProductionBackupError("restore:archive_invalid")
        bundle.extractall(payload, filter="data")
    inventory = json.loads((payload / "objects.json").read_text(encoding="utf-8"))
    actual = []
    objects = payload / "objects"
    for path in sorted(objects.rglob("*")) if objects.exists() else []:
        if path.is_file():
            actual.append(
                {
                    "path": path.relative_to(objects).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    if actual != inventory.get("members"):
        raise ProductionBackupError("restore:object_reconciliation_failed")
    return {
        **restored,
        "databaseDump": str(payload / "database.dump"),
        "objectRoot": str(objects),
        "objectCount": len(actual),
        "objectDigest": inventory.get("digest"),
        "databaseRestoreExecuted": False,
    }


def restore_database_isolated(
    config: dict[str, Any],
    *,
    receipt_path: Path,
    restore_root: Path,
    pg_service_file: Path,
    pg_service: str,
    expected_database: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict[str, Any]:
    """Restore only to an observable empty database whose name is explicitly isolated."""
    _private_file(pg_service_file, maximum_bytes=16_384)
    if not SAFE_ID.fullmatch(pg_service) or not re.fullmatch(
        r"^base2_(?:restore|preview|test)_[a-z0-9_]{3,48}$", expected_database
    ):
        raise ProductionBackupError("restore:database_target_invalid")
    restored = isolated_restore(config, receipt_path=receipt_path, restore_root=restore_root)
    environment = {"PATH": os.environ.get("PATH", ""), "PGSERVICEFILE": str(pg_service_file)}

    def run_checked(command: list[str], error: str):
        completed = runner(
            command,
            env=environment,
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
        if completed.returncode != 0:
            raise ProductionBackupError(error)
        return completed.stdout.strip()

    identity = run_checked(
        [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            f"service={pg_service}",
            "--command",
            "SELECT current_database()",
        ],
        "restore:database_probe_failed",
    )
    if identity != expected_database:
        raise ProductionBackupError("restore:database_target_invalid")
    table_query = (
        "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n "
        "ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p') AND "
        "n.nspname NOT IN ('pg_catalog','information_schema')"
    )
    if (
        run_checked(
            [
                "psql",
                "--no-psqlrc",
                "--tuples-only",
                "--no-align",
                f"service={pg_service}",
                "--command",
                table_query,
            ],
            "restore:database_probe_failed",
        )
        != "0"
    ):
        raise ProductionBackupError("restore:database_not_empty")
    run_checked(
        [
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            f"service={pg_service}",
            restored["databaseDump"],
        ],
        "restore:pg_restore_failed",
    )
    after = run_checked(
        [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            f"service={pg_service}",
            "--command",
            table_query,
        ],
        "restore:database_probe_failed",
    )
    if not after.isdigit() or int(after) < 1:
        raise ProductionBackupError("restore:database_reconciliation_failed")
    restored_schema = run_checked(
        [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            f"service={pg_service}",
            "--command",
            "SELECT COALESCE(MAX((regexp_match(name, '^[0-9]+'))[1]::int),0) "
            "FROM django_migrations WHERE app='sitecontent'",
        ],
        "restore:schema_probe_failed",
    )
    if not restored_schema.isdigit() or int(restored_schema) != config["dataSchema"]:
        raise ProductionBackupError("restore:schema_mismatch")
    restored_references = run_checked(
        [
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            f"service={pg_service}",
            "--command",
            OBJECT_REFERENCE_SQL,
        ],
        "restore:object_reference_ledger_invalid",
    )
    _verify_object_references(
        restored_references,
        object_root=Path(restored["objectRoot"]),
        key=config["_object_key"],
    )
    restore_digest = hashlib.sha256(
        _canonical(
            {
                "backup": restored["sha256"],
                "database": expected_database,
                "tables": int(after),
                "objects": restored["objectDigest"],
            }
        )
    ).hexdigest()
    _write_operations_receipt(
        config,
        kind="restore",
        artifact_digest=restore_digest,
        now=datetime.now(UTC),
    )
    return {
        **restored,
        "database": expected_database,
        "databaseTableCount": int(after),
        "databaseRestoreExecuted": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("backup", "verify", "prune", "restore-isolated", "restore-database-isolated"),
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--restore-root", type=Path)
    parser.add_argument("--restore-pg-service-file", type=Path)
    parser.add_argument("--restore-pg-service")
    parser.add_argument("--restore-database")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.mode == "backup":
        result = create_production_backup(config)
    elif args.mode == "prune":
        result = prune_owned_backups(config)
    elif args.mode == "verify":
        if args.receipt is None:
            raise ProductionBackupError("backup:receipt_required")
        receipt = json.loads(_private_file(args.receipt, maximum_bytes=32_768))
        backup = verify_receipt(receipt, key=config["_key"], backup_root=Path(config["backupRoot"]))
        result = {"status": "verified", "backupFile": backup.name}
    elif args.mode == "restore-isolated":
        if args.receipt is None or args.restore_root is None:
            raise ProductionBackupError("restore:input_required")
        result = isolated_restore(config, receipt_path=args.receipt, restore_root=args.restore_root)
    else:
        if (
            args.receipt is None
            or args.restore_root is None
            or args.restore_pg_service_file is None
            or not args.restore_pg_service
            or not args.restore_database
        ):
            raise ProductionBackupError("restore:input_required")
        result = restore_database_isolated(
            config,
            receipt_path=args.receipt,
            restore_root=args.restore_root,
            pg_service_file=args.restore_pg_service_file,
            pg_service=args.restore_pg_service,
            expected_database=args.restore_database,
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
