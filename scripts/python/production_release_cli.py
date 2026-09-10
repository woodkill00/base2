#!/usr/bin/env python3
"""Single typed entrypoint for provider-neutral Base2 release transitions."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.python.production_release import (
    ProductionReleaseController,
    ReleaseError,
    validate_health_receipt,
    validate_operation_receipt,
)


def _private_key(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ReleaseError("release:key_file_unsafe")
    value = path.read_bytes().strip()
    if len(value) < 32:
        raise ReleaseError("release:key_invalid")
    return value


def _json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ReleaseError("release:input_unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError("release:input_invalid") from exc
    if not isinstance(value, dict):
        raise ReleaseError("release:input_invalid")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "prepare",
            "preview",
            "stage",
            "canary",
            "promote",
            "rollback",
            "status",
            "evidence",
        ],
    )
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--release-key-file", type=Path, required=True)
    parser.add_argument("--approval-key-file", type=Path, required=True)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--environment", choices=["development", "test", "preview", "staging"])
    parser.add_argument("--operation-receipt", type=Path)
    parser.add_argument("--operation-key-file", type=Path)
    parser.add_argument("--health-receipt", type=Path)
    parser.add_argument("--health-key-file", type=Path)
    args = parser.parse_args(argv)
    try:
        release_key = _private_key(args.release_key_file)
        approval_key = _private_key(args.approval_key_file)
        controller = ProductionReleaseController(
            args.journal,
            release_key=release_key,
            approval_key=approval_key,
        )
        if args.action in {"status", "evidence"}:
            result = controller.status()
        else:
            if args.release is None or args.approval is None or args.environment is None:
                raise ReleaseError("release:arguments_incomplete")
            candidate = _json(args.release)
            owner_approval = _json(args.approval)
            execute = None
            health = None
            if args.action not in {"prepare", "preview"}:
                if args.operation_receipt is None or args.operation_key_file is None:
                    raise ReleaseError("release:operation_receipt_required")
                receipt = _json(args.operation_receipt)
                admitted_operation = None
                operation_key = _private_key(args.operation_key_file)
                if operation_key in {release_key, approval_key}:
                    raise ReleaseError("release:key_scope_invalid")

                def execute(action, release, environment, operation_id, reconcile_only):
                    nonlocal admitted_operation
                    del reconcile_only
                    admitted_operation = validate_operation_receipt(
                        receipt,
                        action=action,
                        release_id=release["releaseId"],
                        environment=environment,
                        source_commit=release["sourceCommit"],
                        artifact_digest=release["artifactDigest"],
                        operation_id=operation_id,
                        now=datetime.now(UTC),
                        key=operation_key,
                    )
                    return admitted_operation

                if args.action in {"stage", "canary", "promote"}:
                    if args.health_receipt is None or args.health_key_file is None:
                        raise ReleaseError("release:health_receipt_required")
                    health_key = _private_key(args.health_key_file)
                    if health_key in {release_key, approval_key, operation_key}:
                        raise ReleaseError("release:key_scope_invalid")
                    raw_health = _json(args.health_receipt)

                    def health(action):
                        if admitted_operation is None:
                            raise ReleaseError("release:operation_receipt_required")
                        admitted_health = validate_health_receipt(
                            raw_health,
                            action=action,
                            release_id=candidate["releaseId"],
                            environment=args.environment,
                            source_commit=candidate["sourceCommit"],
                            artifact_digest=candidate["artifactDigest"],
                            operation_id=admitted_operation["operationId"],
                            operation_observed_at=datetime.fromisoformat(
                                admitted_operation["observedAt"]
                            ),
                            now=datetime.now(UTC),
                            key=health_key,
                        )
                        return admitted_health["healthy"]

            result = controller.transition(
                action=args.action,
                release=candidate,
                environment=args.environment,
                owner_approval=owner_approval,
                now=datetime.now(UTC),
                health=health,
                execute=execute,
            )
            if result.get("status") in {"pending", "halted"}:
                raise ReleaseError(f'release:{result["status"]}')
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except ReleaseError as exc:
        print(json.dumps({"status": "failed", "errorCode": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
