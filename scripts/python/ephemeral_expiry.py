#!/usr/bin/env python3
"""Durable, bounded expiry registry for exact-owned ephemeral environments."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PLAN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{7,79}$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,127}$")
GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
ADAPTER = "digitalocean-full-preview"
MAXIMUM_PLANS = 64


class EphemeralExpiryError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _signature(value: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()


def _private_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or not path.is_dir() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise EphemeralExpiryError("expiry:private_directory_required")
    return path.resolve(strict=True)


def _private_file(path: Path) -> Path:
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise EphemeralExpiryError("expiry:private_file_required")
    return path.resolve(strict=True)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class ExpiryPlanStore:
    def __init__(self, root: Path, *, key: bytes):
        if len(key) < 32:
            raise EphemeralExpiryError("expiry:key_invalid")
        self.root = _private_directory(root)
        self.plan_root = _private_directory(self.root / "plans")
        self.receipt_root = _private_directory(self.root / "receipts")
        self.failure_root = _private_directory(self.root / "failures")
        self.key = key

    def register(self, plan: dict[str, Any]) -> dict[str, Any]:
        validated = self._validate(plan)
        path = self.plan_root / f"{validated['planId']}.json"
        signed = {**validated, "signature": _signature(validated, self.key)}
        if path.exists():
            if self.load(validated["planId"]) != signed:
                raise EphemeralExpiryError("expiry:plan_conflict")
            return signed
        if len(list(self.plan_root.glob("*.json"))) >= MAXIMUM_PLANS:
            raise EphemeralExpiryError("expiry:plan_capacity_exceeded")
        _atomic_json(path, signed)
        return signed

    def load(self, plan_id: str) -> dict[str, Any]:
        if not PLAN_ID.fullmatch(plan_id):
            raise EphemeralExpiryError("expiry:plan_id_invalid")
        path = _private_file(self.plan_root / f"{plan_id}.json")
        value = json.loads(path.read_text(encoding="utf-8"))
        signature = value.pop("signature", "") if isinstance(value, dict) else ""
        validated = self._validate(value)
        if not hmac.compare_digest(str(signature), _signature(validated, self.key)):
            raise EphemeralExpiryError("expiry:plan_integrity")
        return {**validated, "signature": signature}

    def plans(self) -> list[dict[str, Any]]:
        paths = sorted(self.plan_root.glob("*.json"))
        if len(paths) > MAXIMUM_PLANS:
            raise EphemeralExpiryError("expiry:plan_capacity_exceeded")
        if any(path.is_symlink() or not PLAN_ID.fullmatch(path.stem) for path in paths):
            raise EphemeralExpiryError("expiry:unsafe_plan_member")
        return [self.load(path.stem) for path in paths]

    def plan_members(self) -> list[Path]:
        paths = sorted(self.plan_root.glob("*.json"))
        if len(paths) > MAXIMUM_PLANS:
            raise EphemeralExpiryError("expiry:plan_capacity_exceeded")
        return paths

    def record_failure(self, member: str, error_code: str) -> dict[str, Any]:
        safe_id = hashlib.sha256(member.encode()).hexdigest()[:24]
        body = {
            "schemaVersion": 1,
            "memberDigest": safe_id,
            "status": "failed",
            "errorCode": error_code,
        }
        receipt = {**body, "signature": _signature(body, self.key)}
        _atomic_json(self.failure_root / f"{safe_id}.json", receipt)
        return receipt

    def receipt(self, plan: dict[str, Any]) -> dict[str, Any] | None:
        path = self.receipt_root / f"{plan['planId']}.json"
        if not path.exists():
            return None
        value = json.loads(_private_file(path).read_text(encoding="utf-8"))
        signature = value.pop("signature", "") if isinstance(value, dict) else ""
        if (
            set(value) != {"schemaVersion", "planId", "planDigest", "status", "adapterReceipt"}
            or value.get("planId") != plan["planId"]
            or value.get("planDigest") != hashlib.sha256(_canonical(plan)).hexdigest()
            or value.get("status") != "destroyed"
            or not hmac.compare_digest(str(signature), _signature(value, self.key))
        ):
            raise EphemeralExpiryError("expiry:receipt_integrity")
        return {**value, "signature": signature}

    def settle(self, plan: dict[str, Any], adapter_receipt: dict[str, Any]) -> dict[str, Any]:
        body = {
            "schemaVersion": 1,
            "planId": plan["planId"],
            "planDigest": hashlib.sha256(_canonical(plan)).hexdigest(),
            "status": "destroyed",
            "adapterReceipt": adapter_receipt,
        }
        receipt = {**body, "signature": _signature(body, self.key)}
        _atomic_json(self.receipt_root / f"{plan['planId']}.json", receipt)
        return receipt

    @staticmethod
    def _validate(plan: object) -> dict[str, Any]:
        required = {
            "schemaVersion",
            "planId",
            "adapter",
            "sourceCommit",
            "expiresAt",
            "runId",
            "stateRoot",
            "credentialFile",
            "ownedResources",
        }
        if not isinstance(plan, dict) or set(plan) != required or plan.get("schemaVersion") != 1:
            raise EphemeralExpiryError("expiry:plan_invalid")
        if (
            not PLAN_ID.fullmatch(str(plan["planId"]))
            or plan["adapter"] != ADAPTER
            or not GIT_COMMIT.fullmatch(str(plan["sourceCommit"]))
            or not RUN_ID.fullmatch(str(plan["runId"]))
            or not isinstance(plan["ownedResources"], list)
            or not plan["ownedResources"]
            or len(plan["ownedResources"]) > 32
            or len(set(plan["ownedResources"])) != len(plan["ownedResources"])
            or not all(RUN_ID.fullmatch(str(item)) for item in plan["ownedResources"])
            or plan["ownedResources"] != [plan["runId"]]
        ):
            raise EphemeralExpiryError("expiry:plan_invalid")
        try:
            deadline = datetime.fromisoformat(str(plan["expiresAt"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise EphemeralExpiryError("expiry:plan_invalid") from exc
        if deadline.tzinfo is None:
            raise EphemeralExpiryError("expiry:plan_invalid")
        for key in ("stateRoot", "credentialFile"):
            value = Path(str(plan[key]))
            if not value.is_absolute() or ".." in value.parts:
                raise EphemeralExpiryError("expiry:plan_invalid")
        return dict(plan)


def scan_due(
    store: ExpiryPlanStore,
    *,
    now: datetime,
    adapters: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
) -> dict[str, Any]:
    if now.tzinfo is None or set(adapters) != {ADAPTER}:
        raise EphemeralExpiryError("expiry:scanner_configuration_invalid")
    destroyed: list[str] = []
    pending: list[str] = []
    replayed: list[str] = []
    failed: list[str] = []
    for path in store.plan_members():
        member = path.name
        try:
            if path.is_symlink() or not PLAN_ID.fullmatch(path.stem):
                raise EphemeralExpiryError("expiry:unsafe_plan_member")
            plan = store.load(path.stem)
            if store.receipt(plan):
                replayed.append(plan["planId"])
                continue
            deadline = datetime.fromisoformat(plan["expiresAt"].replace("Z", "+00:00"))
            if now.astimezone(UTC) < deadline.astimezone(UTC):
                pending.append(plan["planId"])
                continue
            result = adapters[plan["adapter"]](plan)
            if (
                not isinstance(result, dict)
                or result.get("state") != "destroyed"
                or result.get("runId") != plan["runId"]
                or result.get("secretValuesEmitted") != 0
            ):
                raise EphemeralExpiryError("expiry:adapter_not_terminal")
            store.settle(plan, result)
            destroyed.append(plan["planId"])
        except (EphemeralExpiryError, OSError, ValueError, json.JSONDecodeError) as exc:
            error_code = str(exc) if isinstance(exc, EphemeralExpiryError) else "expiry:plan_rejected"
            store.record_failure(member, error_code)
            failed.append(hashlib.sha256(member.encode()).hexdigest()[:24])
        except Exception:
            # Adapters are an isolation boundary. Their implementation errors
            # must not suppress later exact-owned expiry plans or leak details.
            store.record_failure(member, "expiry:adapter_failed")
            failed.append(hashlib.sha256(member.encode()).hexdigest()[:24])
    return {
        "status": "complete",
        "scanned": len(destroyed) + len(pending) + len(replayed) + len(failed),
        "destroyed": destroyed,
        "pending": pending,
        "replayed": replayed,
        "failed": failed,
        "secretValuesEmitted": 0,
    }


def _digitalocean_adapter(plan: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "digital_ocean.scripts.python.full_preview_expire",
            "--state-root",
            plan["stateRoot"],
            "--run-id",
            plan["runId"],
            "--credential-file",
            plan["credentialFile"],
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(Path.cwd())},
    )
    if completed.returncode != 0:
        raise EphemeralExpiryError("expiry:adapter_failed")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise EphemeralExpiryError("expiry:adapter_receipt_invalid") from exc


def _key(path: Path) -> bytes:
    return _private_file(path).read_bytes().strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--register-plan", type=Path)
    args = parser.parse_args(argv)
    store = ExpiryPlanStore(args.root, key=_key(args.key_file))
    if args.register_plan:
        source = json.loads(_private_file(args.register_plan).read_text(encoding="utf-8"))
        result = store.register(source)
        print(json.dumps({"status": "registered", "planId": result["planId"]}, sort_keys=True))
        return 0
    result = scan_due(
        store,
        now=datetime.now(UTC),
        adapters={ADAPTER: _digitalocean_adapter},
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
