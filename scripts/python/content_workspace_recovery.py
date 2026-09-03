#!/usr/bin/env python3
"""Create and verify encrypted, isolated content-workspace recovery bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.security.secret_box import SecretBox, SecretBoxError  # noqa: E402

COLLECTIONS = (
    "definitions",
    "fields",
    "workflows",
    "records",
    "versions",
    "relationships",
    "views",
    "importJobs",
    "exportJobs",
    "auditReferences",
    "assets",
    "assetBindings",
)
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
SITE_ID = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
MAX_MEMBERS = 100_000
MAX_PLAINTEXT_BYTES = 100 * 1024 * 1024


class RecoveryError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _identifiers(rows: list[dict], collection: str) -> set[str]:
    values = set()
    for row in rows:
        if not isinstance(row, dict) or not ID.fullmatch(str(row.get("id", ""))):
            raise RecoveryError(f"workspace_recovery_{collection}_invalid")
        if row["id"] in values:
            raise RecoveryError(f"workspace_recovery_{collection}_duplicate")
        values.add(row["id"])
    return values


def validate_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "schemaVersion",
        "siteId",
        "collections",
    }:
        raise RecoveryError("workspace_recovery_snapshot_invalid")
    if snapshot["schemaVersion"] != 1 or not SITE_ID.fullmatch(str(snapshot["siteId"])):
        raise RecoveryError("workspace_recovery_snapshot_invalid")
    collections = snapshot["collections"]
    if not isinstance(collections, dict) or set(collections) != set(COLLECTIONS):
        raise RecoveryError("workspace_recovery_inventory_invalid")
    total = 0
    ids = {}
    for name in COLLECTIONS:
        rows = collections[name]
        if not isinstance(rows, list):
            raise RecoveryError(f"workspace_recovery_{name}_invalid")
        total += len(rows)
        if total > MAX_MEMBERS:
            raise RecoveryError("workspace_recovery_limit_exceeded")
        ids[name] = _identifiers(rows, name)

    definition_ids = ids["definitions"]
    record_ids = ids["records"]
    asset_ids = ids["assets"]
    for row in collections["records"]:
        if row.get("definitionId") not in definition_ids:
            raise RecoveryError("workspace_recovery_definition_reference_invalid")
    for row in collections["versions"]:
        if row.get("recordId") not in record_ids:
            raise RecoveryError("workspace_recovery_record_reference_invalid")
    for row in collections["relationships"]:
        if row.get("sourceId") not in record_ids or row.get("targetId") not in record_ids:
            raise RecoveryError("workspace_recovery_relationship_reference_invalid")
    for row in collections["assetBindings"]:
        if row.get("recordId") not in record_ids or row.get("assetId") not in asset_ids:
            raise RecoveryError("workspace_recovery_asset_reference_invalid")
    for name in ("importJobs", "exportJobs"):
        for row in collections[name]:
            if row.get("definitionId") not in definition_ids:
                raise RecoveryError("workspace_recovery_job_reference_invalid")

    encoded = _canonical(snapshot)
    if len(encoded) > MAX_PLAINTEXT_BYTES:
        raise RecoveryError("workspace_recovery_limit_exceeded")
    return json.loads(encoded)


def create_bundle(snapshot: Any, key: str) -> dict[str, Any]:
    validated = validate_snapshot(snapshot)
    plaintext = _canonical(validated)
    inventory = {
        name: {
            "count": len(validated["collections"][name]),
            "sha256": hashlib.sha256(_canonical(validated["collections"][name])).hexdigest(),
        }
        for name in COLLECTIONS
    }
    manifest = {
        "schemaVersion": 1,
        "siteRef": hashlib.sha256(validated["siteId"].encode()).hexdigest()[:16],
        "snapshotSha256": hashlib.sha256(plaintext).hexdigest(),
        "byteSize": len(plaintext),
        "inventory": inventory,
    }
    manifest["digest"] = hashlib.sha256(_canonical(manifest)).hexdigest()
    try:
        ciphertext = SecretBox(key).encrypt(plaintext.decode())
    except SecretBoxError as exc:
        raise RecoveryError("workspace_recovery_key_invalid") from exc
    return {"manifest": manifest, "ciphertext": ciphertext}


def restore_bundle(
    bundle: Any, key: str, *, target: Path, live_roots: tuple[Path, ...] = ()
) -> dict:
    resolved = target.expanduser().resolve()
    if resolved.exists() or any(
        resolved == root.resolve() or root.resolve() in resolved.parents for root in live_roots
    ):
        raise RecoveryError("workspace_recovery_target_unsafe")
    if not isinstance(bundle, dict) or set(bundle) != {"manifest", "ciphertext"}:
        raise RecoveryError("workspace_recovery_bundle_invalid")
    manifest = bundle["manifest"]
    supplied_digest = manifest.get("digest", "") if isinstance(manifest, dict) else ""
    unsigned = (
        {key_name: value for key_name, value in manifest.items() if key_name != "digest"}
        if isinstance(manifest, dict)
        else {}
    )
    if not supplied_digest or hashlib.sha256(_canonical(unsigned)).hexdigest() != supplied_digest:
        raise RecoveryError("workspace_recovery_manifest_integrity_failed")
    try:
        plaintext = SecretBox(key).decrypt(bundle["ciphertext"]).encode()
    except (SecretBoxError, TypeError, KeyError) as exc:
        raise RecoveryError("workspace_recovery_ciphertext_integrity_failed") from exc
    if len(plaintext) != manifest.get("byteSize") or hashlib.sha256(
        plaintext
    ).hexdigest() != manifest.get("snapshotSha256"):
        raise RecoveryError("workspace_recovery_snapshot_integrity_failed")
    restored = validate_snapshot(json.loads(plaintext))
    expected = {
        name: {
            "count": len(restored["collections"][name]),
            "sha256": hashlib.sha256(_canonical(restored["collections"][name])).hexdigest(),
        }
        for name in COLLECTIONS
    }
    if expected != manifest.get("inventory"):
        raise RecoveryError("workspace_recovery_inventory_integrity_failed")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(resolved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(plaintext)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "status": "restored",
        "target": str(resolved),
        "manifestDigest": supplied_digest,
        "counts": {name: item["count"] for name, item in expected.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("backup", "restore"))
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    key = os.getenv("CONTENT_WORKSPACE_RECOVERY_KEY", "")
    if not key:
        raise RecoveryError("workspace_recovery_key_missing")
    safe_root = (ROOT / ".artifacts" / "workspace-recovery").resolve()
    source_path = args.source.expanduser().resolve()
    target_path = args.target.expanduser().resolve()
    if safe_root not in source_path.parents or safe_root not in target_path.parents:
        raise RecoveryError("workspace_recovery_path_unsafe")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if args.mode == "backup":
        result = create_bundle(source, key)
        if target_path.exists():
            raise RecoveryError("workspace_recovery_target_unsafe")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True))
            handle.flush()
            os.fsync(handle.fileno())
        print(json.dumps({"status": "backed_up", "manifest": result["manifest"]}, sort_keys=True))
    else:
        result = restore_bundle(
            source, key, target=target_path, live_roots=(ROOT / "data", ROOT / "volumes")
        )
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
