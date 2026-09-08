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
        self.key = key

    def register(self, plan: dict[str, Any]) -> dict[str, Any]:
        validated = self._validate(plan)
        path = self.plan_root / f"{validated['planId']}.json"
        signed = {**validated, "signature": _signature(validated, self.key)}
        if path.exists():
            if self.load(validated["planId"]) != signed:
                raise EphemeralExpiryError("expiry:plan_conflict")
            return signed
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
    for plan in store.plans():
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
    return {
        "status": "complete",
        "scanned": len(destroyed) + len(pending) + len(replayed),
        "destroyed": destroyed,
        "pending": pending,
        "replayed": replayed,
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
