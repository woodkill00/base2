#!/usr/bin/env python3
"""Portable guarded full-preview policy and verification entrypoint."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import stat
from digital_ocean.scripts.python.full_preview_policy import canonical_digest, full_preview_policy, safe_receipt
from digital_ocean.scripts.python.full_preview_probe import safe_json, verify_full_preview

def _private_text(path: Path, label: str) -> str:
    if not path.is_file() or path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError(f"{label} must be an owner-only real file")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{label} is empty")
    return value

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    policy_parser = commands.add_parser("policy")
    policy_parser.add_argument("--domain", required=True)
    policy_parser.add_argument("--owner-cidr", action="append", required=True)
    policy_parser.add_argument("--ttl-minutes", type=int, default=60)
    probe_parser = commands.add_parser("probe")
    probe_parser.add_argument("--domain", required=True)
    probe_parser.add_argument("--ip-address", required=True)
    probe_parser.add_argument("--owner-cidr", action="append", required=True)
    probe_parser.add_argument("--username-file", type=Path, required=True)
    probe_parser.add_argument("--password-file", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "policy":
        policy = full_preview_policy(args.domain, args.owner_cidr, ttl_minutes=args.ttl_minutes)
        receipt = safe_receipt(policy)
        receipt["policyDigest"] = canonical_digest(policy)
        receipt["status"] = "ready_for_live_approval"
        print(json.dumps(receipt, sort_keys=True))
        return 0
    print(safe_json(verify_full_preview(
        args.domain, args.ip_address,
        username=_private_text(args.username_file, "username"),
        password=_private_text(args.password_file, "password"),
        owner_cidrs=args.owner_cidr,
    )))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
