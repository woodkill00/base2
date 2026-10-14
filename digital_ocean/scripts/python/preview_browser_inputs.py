"""Bind existing private owner credentials to an exact, unexpired full preview."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .preview_lease_v2 import FullPreviewLeaseStore, LeaseV2IntegrityError


def current_lease(receipt_path: Path, receipt: dict, run_id: str) -> None:
    """Reject an obsolete launch receipt before resolving owner credentials."""
    if (
        not re.fullmatch(r"base2-full-[0-9]{8}-[0-9]{6}", run_id)
        or receipt_path.name != f"{run_id}.json"
        or receipt_path.parent.name != "evidence"
        or receipt_path.parent.parent.name != run_id
    ):
        raise ValueError("lease_location_invalid")
    root = receipt_path.parent.parent / "leases"
    info = root.stat()
    if (
        root.resolve() != root
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise ValueError("lease_directory_invalid")
    # Check private-file admission as well as the store's schema/digest validation.
    private_json(root / f"{run_id}.json")
    lease = FullPreviewLeaseStore(root).load(run_id)
    if (
        lease["state"] != "live-verified"
        or any(
            lease[key] != receipt.get(key)
            for key in ("runId", "sourceCommit", "profileId", "expiresAt")
        )
        or not lease["droplet"]
        or not any(
            row["domain"] == receipt.get("domain")
            and row["name"] == "@"
            and row["value"] == receipt.get("publicIp")
            and row["state"] == "bound"
            for row in lease["dnsRecords"]
        )
    ):
        raise ValueError("current_lease_invalid")


def private_json(path: Path) -> dict:
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("private_input_path_invalid")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > 16384
        ):
            raise ValueError("private_input_permissions_invalid")
        with os.fdopen(fd, closefd=False) as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError("private_input_shape_invalid")
        return value
    finally:
        os.close(fd)


def browser_environment(
    receipt: dict, owner: dict, *, run_id: str, source_commit: str, now: datetime
) -> dict[str, str]:
    if (
        not re.fullmatch(r"base2-full-[0-9]{8}-[0-9]{6}", run_id)
        or not re.fullmatch(r"[a-f0-9]{40}", source_commit)
        or receipt.get("ok") is not True
        or receipt.get("status") != "live-verified"
        or receipt.get("runId") != run_id
        or receipt.get("sourceCommit") != source_commit
        or receipt.get("profileId") != "base2-obsidian"
        or receipt.get("domain") != "woodkilldev.com"
        or receipt.get("previewMode") != "full"
    ):
        raise ValueError("preview_binding_invalid")
    expiry = datetime.fromisoformat(receipt.get("expiresAt", "").replace("Z", "+00:00"))
    if expiry.tzinfo is None or now.tzinfo is None or expiry <= now:
        raise ValueError("preview_expired")
    address = str(ipaddress.IPv4Address(receipt.get("publicIp", "")))
    if (
        set(owner) != {"email", "password", "display_name", "profile"}
        or any(
            not isinstance(value, str)
            or not value
            or len(value) > 1024
            or any(c in value for c in "\r\n\x00")
            for value in owner.values()
        )
        or owner["profile"] != "base2-obsidian"
        or owner["display_name"] != "woodkill"
        or owner["email"].count("@") != 1
        or any(c.isspace() for c in owner["email"])
    ):
        raise ValueError("owner_identity_invalid")
    return {
        "BASE2_OWNER_EMAIL": owner["email"],
        "BASE2_OWNER_PASSWORD": owner["password"],
        "BASE2_LIVE_SOURCE_COMMIT": source_commit,
        "BASE2_LIVE_RUN_ID": run_id,
        "BASE2_LIVE_DOMAIN": receipt["domain"],
        "BASE2_LIVE_ADDRESS": address,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--owner-file", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    try:
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
            raise ValueError("source_dirty")
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        # Resolve no owner credentials until the receipt has been loaded locally.
        receipt = private_json(args.receipt)
        current_lease(args.receipt, receipt, args.run_id)
        owner = private_json(args.owner_file)
        env = dict(os.environ)
        env.update(
            browser_environment(
                receipt, owner, run_id=args.run_id, source_commit=commit, now=datetime.now(UTC)
            )
        )
        return subprocess.run(
            ["npm", "run", "test:live-full-preview"],
            cwd=root / "react-app",
            env=env,
            check=False,
            timeout=1800,
        ).returncode
    except (OSError, ValueError, TypeError, LeaseV2IntegrityError, subprocess.SubprocessError):
        print("Live acceptance BLOCKED: private inputs, source, lease or runner validation failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
