#!/usr/bin/env python3
"""Authenticated backup and isolated restore primitives for Base2 drills."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from scripts.python.data_readiness import restore_target


class RecoveryDenied(ValueError):
    pass


KEY_REF = re.compile(r"^vaultwarden://[A-Za-z0-9][A-Za-z0-9._/-]{2,254}$")
SAFE_TARGET = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
STREAM_MAGIC = b"BASE2-BACKUP-V2\n"


def _encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decoded(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise RecoveryDenied("backup:encoding_invalid") from exc


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_backup(
    *,
    payload: bytes,
    target_id: str,
    data_schema: int,
    key: bytes,
    key_ref: str,
    output: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not payload or len(payload) > 64 * 1024 * 1024:
        raise RecoveryDenied("backup:payload_invalid")
    if not SAFE_TARGET.fullmatch(target_id or "") or data_schema < 1:
        raise RecoveryDenied("backup:target_invalid")
    if len(key) != 32 or not KEY_REF.fullmatch(key_ref or ""):
        raise RecoveryDenied("backup:key_invalid")
    created = (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
    metadata = {
        "schemaVersion": 1,
        "targetId": target_id,
        "dataSchema": data_schema,
        "createdAt": created,
        "keyRef": key_ref,
    }
    aad = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, payload, aad)
    envelope = {
        **metadata,
        "algorithm": "AES-256-GCM",
        "nonce": _encoded(nonce),
        "ciphertext": _encoded(ciphertext),
        "plaintextSha256": hashlib.sha256(payload).hexdigest(),
        "plaintextSize": len(payload),
        "complete": True,
    }
    _atomic(output, envelope)
    return {
        "schemaVersion": 1,
        "targetId": target_id,
        "dataSchema": data_schema,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "plaintextSha256": envelope["plaintextSha256"],
        "size": output.stat().st_size,
        "encrypted": True,
        "keyRef": key_ref,
        "createdAt": created,
    }


def restore_isolated(
    *,
    backup: Path,
    key: bytes,
    expected_target: str,
    expected_schema: int,
    output: Path,
    target_class: str = "isolated",
) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise RecoveryDenied("restore:target_must_be_absent")
    restore_target(
        target_id=expected_target,
        target_class=target_class,
        target_path=output,
    )
    try:
        envelope = json.loads(backup.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryDenied("restore:backup_invalid") from exc
    required = {
        "schemaVersion",
        "targetId",
        "dataSchema",
        "createdAt",
        "keyRef",
        "algorithm",
        "nonce",
        "ciphertext",
        "plaintextSha256",
        "plaintextSize",
        "complete",
    }
    if (
        not isinstance(envelope, dict)
        or set(envelope) != required
        or envelope.get("schemaVersion") != 1
        or envelope.get("complete") is not True
    ):
        raise RecoveryDenied("restore:backup_invalid")
    if envelope["targetId"] != expected_target:
        raise RecoveryDenied("restore:wrong_target")
    if envelope["dataSchema"] != expected_schema:
        raise RecoveryDenied("restore:schema_mismatch")
    if len(key) != 32 or envelope["algorithm"] != "AES-256-GCM":
        raise RecoveryDenied("restore:key_invalid")
    metadata = {
        name: envelope[name]
        for name in ("schemaVersion", "targetId", "dataSchema", "createdAt", "keyRef")
    }
    aad = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    try:
        plaintext = AESGCM(key).decrypt(
            _decoded(envelope["nonce"]), _decoded(envelope["ciphertext"]), aad
        )
    except Exception as exc:
        raise RecoveryDenied("restore:integrity_failed") from exc
    if (
        len(plaintext) != envelope["plaintextSize"]
        or hashlib.sha256(plaintext).hexdigest() != envelope["plaintextSha256"]
    ):
        raise RecoveryDenied("restore:integrity_failed")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(plaintext)
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "targetId": expected_target,
        "targetClass": target_class,
        "dataSchema": expected_schema,
        "sha256": hashlib.sha256(plaintext).hexdigest(),
        "size": len(plaintext),
        "isolated": True,
    }


def migration_preflight(
    *, current_schema: int, target_schema: int, backup_schema: int
) -> dict[str, Any]:
    if min(current_schema, target_schema, backup_schema) < 1:
        raise RecoveryDenied("migration:schema_invalid")
    if target_schema < current_schema:
        raise RecoveryDenied("migration:downgrade_denied")
    if backup_schema != current_schema:
        raise RecoveryDenied("migration:backup_stale")
    return {
        "allowed": True,
        "fromSchema": current_schema,
        "toSchema": target_schema,
        "rollbackSchema": backup_schema,
    }


def certificate_drill(*, acme_mode: str, days_remaining: int) -> dict[str, Any]:
    if acme_mode != "staging":
        raise RecoveryDenied("certificate:production_forbidden")
    if days_remaining < 0:
        raise RecoveryDenied("certificate:expired")
    return {"mode": "staging", "renewalRequired": days_remaining <= 30, "liveIssuance": False}


def preview_snapshot(
    *,
    lease_id: str,
    payload: bytes,
    key: bytes,
    key_ref: str,
    output: Path,
    verified_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    started = time.monotonic()
    receipt = create_backup(
        payload=payload,
        target_id=lease_id,
        data_schema=1,
        key=key,
        key_ref=key_ref,
        output=output,
        now=verified_at,
    )
    if expires_at.astimezone(UTC) <= verified_at.astimezone(UTC):
        output.unlink(missing_ok=True)
        raise RecoveryDenied("snapshot:expiry_invalid")
    return {
        "schemaVersion": 1,
        "leaseId": lease_id,
        "status": "complete",
        "sha256": receipt["sha256"],
        "size": receipt["size"],
        "encrypted": True,
        "keyRef": key_ref,
        "verifiedAt": verified_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "retentionExpiresAt": expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "durationMs": round((time.monotonic() - started) * 1000, 3),
    }


def object_inventory(root: Path, *, maximum_files: int = 10000) -> dict[str, Any]:
    base = root.resolve()
    if root.is_symlink() or not base.is_dir() or not 1 <= maximum_files <= 100000:
        raise RecoveryDenied("backup:object_root_invalid")
    members = []
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            raise RecoveryDenied("backup:object_symlink_denied")
        if not path.is_file():
            continue
        if len(members) >= maximum_files:
            raise RecoveryDenied("backup:object_limit_exceeded")
        relative = path.relative_to(base).as_posix()
        member_digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                member_digest.update(chunk)
        members.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": member_digest.hexdigest(),
            }
        )
    return {
        "schemaVersion": 1,
        "count": len(members),
        "members": members,
        "digest": hashlib.sha256(
            json.dumps(members, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def create_stream_backup(
    *,
    source: Path,
    target_id: str,
    data_schema: int,
    key: bytes,
    key_ref: str,
    output: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 8 * 1024**3:
        raise RecoveryDenied("backup:source_invalid")
    if not SAFE_TARGET.fullmatch(target_id or "") or data_schema < 1:
        raise RecoveryDenied("backup:target_invalid")
    if len(key) != 32 or not KEY_REF.fullmatch(key_ref or ""):
        raise RecoveryDenied("backup:key_invalid")
    created = (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
    plaintext_digest = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            plaintext_digest.update(chunk)
    nonce = os.urandom(12)
    metadata = {
        "schemaVersion": 2,
        "targetId": target_id,
        "dataSchema": data_schema,
        "createdAt": created,
        "keyRef": key_ref,
        "algorithm": "AES-256-GCM-stream",
        "nonce": _encoded(nonce),
        "plaintextSha256": plaintext_digest.hexdigest(),
        "plaintextSize": source.stat().st_size,
    }
    header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        os.fchmod(descriptor, 0o600)
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(header)
        with os.fdopen(descriptor, "wb") as destination, source.open("rb") as plaintext:
            destination.write(STREAM_MAGIC)
            destination.write(len(header).to_bytes(4, "big"))
            destination.write(header)
            while chunk := plaintext.read(1024 * 1024):
                destination.write(encryptor.update(chunk))
            destination.write(encryptor.finalize())
            destination.write(encryptor.tag)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {
        **metadata,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "size": output.stat().st_size,
        "encrypted": True,
    }


def restore_stream_backup(
    *,
    backup: Path,
    key: bytes,
    expected_target: str,
    expected_schema: int,
    output: Path,
    target_class: str = "isolated",
) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise RecoveryDenied("restore:target_must_be_absent")
    restore_target(target_id=expected_target, target_class=target_class, target_path=output)
    if backup.is_symlink() or not backup.is_file() or len(key) != 32:
        raise RecoveryDenied("restore:backup_invalid")
    with backup.open("rb") as source:
        if source.read(len(STREAM_MAGIC)) != STREAM_MAGIC:
            raise RecoveryDenied("restore:backup_invalid")
        header_size = int.from_bytes(source.read(4), "big")
        if not 1 <= header_size <= 16384:
            raise RecoveryDenied("restore:backup_invalid")
        header = source.read(header_size)
        try:
            metadata = json.loads(header)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RecoveryDenied("restore:backup_invalid") from exc
        required = {
            "schemaVersion",
            "targetId",
            "dataSchema",
            "createdAt",
            "keyRef",
            "algorithm",
            "nonce",
            "plaintextSha256",
            "plaintextSize",
        }
        if (
            not isinstance(metadata, dict)
            or set(metadata) != required
            or metadata["schemaVersion"] != 2
            or metadata["algorithm"] != "AES-256-GCM-stream"
            or metadata["targetId"] != expected_target
            or metadata["dataSchema"] != expected_schema
            or type(metadata["plaintextSize"]) is not int
            or metadata["plaintextSize"] < 1
            or not re.fullmatch(r"[0-9a-f]{64}", str(metadata["plaintextSha256"]))
            or not KEY_REF.fullmatch(str(metadata["keyRef"]))
        ):
            raise RecoveryDenied("restore:backup_invalid")
        ciphertext_start = len(STREAM_MAGIC) + 4 + header_size
        ciphertext_size = backup.stat().st_size - ciphertext_start - 16
        if ciphertext_size != metadata["plaintextSize"] or ciphertext_size < 1:
            raise RecoveryDenied("restore:backup_invalid")
        source.seek(-16, os.SEEK_END)
        tag = source.read(16)
        source.seek(ciphertext_start)
        decryptor = Cipher(
            algorithms.AES(key), modes.GCM(_decoded(metadata["nonce"]), tag)
        ).decryptor()
        decryptor.authenticate_additional_data(header)
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
        digest = hashlib.sha256()
        remaining = ciphertext_size
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as destination:
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RecoveryDenied("restore:backup_invalid")
                    remaining -= len(chunk)
                    plaintext = decryptor.update(chunk)
                    digest.update(plaintext)
                    destination.write(plaintext)
                try:
                    final = decryptor.finalize()
                except Exception as exc:
                    raise RecoveryDenied("restore:integrity_failed") from exc
                digest.update(final)
                destination.write(final)
                destination.flush()
                os.fsync(destination.fileno())
            if digest.hexdigest() != metadata["plaintextSha256"]:
                raise RecoveryDenied("restore:integrity_failed")
            os.replace(temporary, output)
            os.chmod(output, 0o600)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return {
        "targetId": expected_target,
        "targetClass": target_class,
        "dataSchema": expected_schema,
        "sha256": digest.hexdigest(),
        "size": output.stat().st_size,
        "isolated": True,
    }


def create_database_object_bundle(
    *,
    database_dump: Path,
    object_root: Path,
    output: Path,
    target_id: str,
    data_schema: int,
    key: bytes,
    key_ref: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    inventory = object_inventory(object_root)
    with tempfile.TemporaryDirectory(prefix="base2-backup-bundle-") as temporary:
        root = Path(temporary)
        snapshot = root / "objects"
        snapshot.mkdir(mode=0o700)
        # Copy every object once into a private stable boundary while hashing
        # those exact bytes. The archive never reopens the live source tree.
        for member in inventory["members"]:
            source = object_root.resolve() / member["path"]
            target = snapshot / member["path"]
            if source.is_symlink() or not source.is_file():
                raise RecoveryDenied("backup:object_changed")
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            digest = hashlib.sha256()
            size = 0
            with source.open("rb") as input_stream, target.open("xb") as output_stream:
                while chunk := input_stream.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    output_stream.write(chunk)
                output_stream.flush()
                os.fsync(output_stream.fileno())
            target.chmod(0o600)
            if digest.hexdigest() != member["sha256"] or size != member["size"]:
                raise RecoveryDenied("backup:object_changed")
        manifest = root / "objects.json"
        manifest.write_text(json.dumps(inventory, sort_keys=True), encoding="utf-8")
        archive = root / "recovery.tar"
        with tarfile.open(archive, "w") as bundle:
            bundle.add(database_dump, arcname="database.dump", recursive=False)
            bundle.add(manifest, arcname="objects.json", recursive=False)
            # Inventory and payload are one encrypted recovery unit. Every name
            # is derived from the verified private snapshot, never a second
            # read of the mutable live object tree.
            for member in inventory["members"]:
                bundle.add(
                    snapshot / member["path"],
                    arcname=f"objects/{member['path']}",
                    recursive=False,
                )
        receipt = create_stream_backup(
            source=archive,
            target_id=target_id,
            data_schema=data_schema,
            key=key,
            key_ref=key_ref,
            output=output,
            now=now,
        )
    return {**receipt, "objectCount": inventory["count"], "objectDigest": inventory["digest"]}
