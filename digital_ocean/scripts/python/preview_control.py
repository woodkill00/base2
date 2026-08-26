#!/usr/bin/env python3
"""Unified bounded control plane for Base2 full-preview operations."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path

from digital_ocean.scripts.python.full_preview_expire import _token
from digital_ocean.scripts.python.live_preview_provider import DigitalOceanHttpClient
from digital_ocean.scripts.python.preview_dns_convergence import (
    DnsConvergenceError,
    classify_dns_observation,
)
from digital_ocean.scripts.python.preview_expiry import (
    ExpiryPlanError,
    arm_expiry,
    build_expiry_plan,
    extend_lease,
)
from digital_ocean.scripts.python.preview_inventory import (
    InventoryError,
    admit_private_root,
    inventory,
)
from digital_ocean.scripts.python.preview_provider_inventory import (
    ProviderInventoryError,
    reconcile_provider_inventory,
)
from digital_ocean.scripts.python.preview_retention import RetentionError, cleanup_visual_evidence
from digital_ocean.scripts.python.preview_runtime import RuntimeAdmissionError, inspect_runtime
from digital_ocean.scripts.python.preview_visual_evidence import (
    VisualEvidenceError,
    build_visual_bundle,
)

RUN_ID = re.compile(r"^base2-full-[0-9]{8}-[0-9]{6}$")
SECRET_PATTERN = re.compile(
    r"(?i)(?:gh[pousr]_[A-Za-z0-9_]{20,}|dop_v1_[A-Fa-f0-9]{32,}|bearer\s+[A-Za-z0-9._~-]{16,})"
)
EXIT_CODES = {
    "OK": 0,
    "RUNTIME_WINDOWS_TOOL": 2,
    "RUNTIME_NON_WSL_REPOSITORY": 2,
    "RUNTIME_NOT_WSL": 2,
    "RUNTIME_ARCH_INVALID": 2,
    "RUNTIME_TOOL_MISSING": 2,
    "RUNTIME_TOOL_UNREADABLE": 2,
    "RUNTIME_TOOL_INVALID": 2,
    "STATE_PERMISSION_INVALID": 3,
    "LEASE_INTEGRITY_INVALID": 3,
    "LEASE_CONFLICT": 3,
    "DNS_OBSERVATION_INVALID": 4,
    "DNS_STALE_RECURSIVE": 4,
    "DNS_SPLIT_VIEW": 4,
    "DNS_UNEXPECTED_IPV6": 4,
    "EVIDENCE_INVALID": 4,
    "EVIDENCE_INCOMPLETE": 4,
    "EXPIRY_NOT_ARMED": 5,
    "EXPIRY_PLAN_DRIFT": 5,
    "LAUNCH_CONFIG_INVALID": 5,
    "SOURCE_NOT_EXACT_MAIN": 5,
    "LIFECYCLE_EXTERNAL_FAILURE": 5,
    "CLEANUP_RECONCILIATION_REQUIRED": 5,
    "PROVIDER_RATE_LIMITED": 5,
}

LAUNCH_FIELDS = {
    "schemaVersion",
    "repoRoot",
    "stateRoot",
    "runId",
    "domain",
    "ownerCidr",
    "ttlMinutes",
    "profilePath",
    "credentialFile",
    "sourceArchiveDir",
    "sshPrivateKey",
    "sshKeyId",
    "operatorAuthFile",
    "flowerAuthFile",
    "probeUsernameFile",
    "probePasswordFile",
    "djangoUsernameFile",
    "djangoEmailFile",
    "djangoPasswordFile",
    "pgadminEmailFile",
    "pgadminPasswordFile",
    "pythonExecutable",
}


class PreviewControlError(RuntimeError):
    def __init__(self, code: str, message: str, *, cleanup_state: str = "not-required"):
        super().__init__(message)
        self.code = code
        self.cleanup_state = cleanup_state


def _sanitize(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = "".join(character if character.isprintable() else "?" for character in text)
    return SECRET_PATTERN.sub("[REDACTED]", text)[:500]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _receipt(
    command: str,
    *,
    ok: bool,
    code: str,
    details: object,
    summary: str,
    cleanup_state: str = "not-required",
) -> dict:
    safe_summary = _sanitize(summary)
    safe_details = details
    receipt = {
        "schemaVersion": 1,
        "ok": ok,
        "command": command,
        "code": code,
        "summary": safe_summary,
        "details": safe_details,
        "cleanupState": cleanup_state,
        "recommendedAction": "none" if ok else _recommend(code),
        "secretValuesEmitted": 0,
    }
    receipt["requestDigest"] = _digest({"command": command, "code": code, "details": safe_details})
    return receipt


def _recommend(code: str) -> str:
    return {
        "RUNTIME_WINDOWS_TOOL": "use the native WSL Linux runtime and clear the shell command hash",
        "RUNTIME_NON_WSL_REPOSITORY": "use the checkout under /home/woodkill/code/base2",
        "DNS_STALE_RECURSIVE": "retain exact-address verification and wait for recursive TTL expiry",
        "DNS_SPLIT_VIEW": "repair or wait for authoritative and public DNS convergence",
        "DNS_UNEXPECTED_IPV6": "remove unexpected AAAA records by exact provider identity",
        "EXPIRY_NOT_ARMED": "perform exact lease cleanup or arm the fixed persistent timer",
        "EVIDENCE_INCOMPLETE": "capture every declared visual surface before approval",
        "SOURCE_NOT_EXACT_MAIN": "clean and synchronize local main with origin/main",
        "CLEANUP_RECONCILIATION_REQUIRED": "reconcile the exact admission tag and lease identities",
    }.get(code, "inspect the sanitized evidence and retry only after the condition is corrected")


def _private_json(path: str | os.PathLike[str], *, code: str) -> dict:
    candidate = Path(path)
    if (
        candidate.is_symlink()
        or not candidate.is_file()
        or stat.S_IMODE(candidate.stat().st_mode) & 0o077
    ):
        raise PreviewControlError(code, "input must be an owner-only real file")
    if candidate.stat().st_size > 131_072:
        raise PreviewControlError(code, "input exceeds safe size")
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PreviewControlError(code, "input is not valid JSON") from exc
    if not isinstance(value, dict):
        raise PreviewControlError(code, "input JSON must be an object")
    return value


@contextmanager
def mutation_lock(state_root: str | os.PathLike[str]):
    root = admit_private_root(state_root, create=True)
    descriptor = os.open(root / ".preview-control.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PreviewControlError(
                "LEASE_CONFLICT", "another lifecycle mutation is active"
            ) from exc
        yield root
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _run_json(
    args: list[str], *, cwd: Path, runner: Callable = subprocess.run, timeout: int = 1800
) -> dict:
    completed = runner(args, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        raise PreviewControlError("LIFECYCLE_EXTERNAL_FAILURE", "fixed lifecycle operation failed")
    try:
        value = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise PreviewControlError(
            "LIFECYCLE_EXTERNAL_FAILURE", "lifecycle receipt was invalid"
        ) from exc
    if not isinstance(value, dict) or value.get("secretValuesEmitted") != 0:
        raise PreviewControlError(
            "LIFECYCLE_EXTERNAL_FAILURE", "lifecycle receipt violated output contract"
        )
    return value


def prove_exact_main(repo: Path, *, runner: Callable = subprocess.run) -> str:
    status = runner(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise PreviewControlError("SOURCE_NOT_EXACT_MAIN", "source is not clean exact main")
    commands = (
        ["git", "rev-parse", "HEAD"],
        ["git", "rev-parse", "main"],
        ["git", "rev-parse", "origin/main"],
    )
    outputs = []
    for command in commands:
        completed = runner(
            command, cwd=repo, check=False, capture_output=True, text=True, timeout=20
        )
        if completed.returncode != 0:
            raise PreviewControlError("SOURCE_NOT_EXACT_MAIN", "Git source admission failed")
        outputs.append(completed.stdout.strip())
    if not outputs[0] or len(set(outputs)) != 1:
        raise PreviewControlError("SOURCE_NOT_EXACT_MAIN", "source is not clean exact main")
    if not re.fullmatch(r"[0-9a-f]{40}", outputs[0]):
        raise PreviewControlError("SOURCE_NOT_EXACT_MAIN", "source commit is invalid")
    return outputs[0]


def validate_launch_config(value: dict) -> dict:
    if set(value) != LAUNCH_FIELDS or value.get("schemaVersion") != 1:
        raise PreviewControlError("LAUNCH_CONFIG_INVALID", "launch configuration shape is invalid")
    if not RUN_ID.fullmatch(str(value.get("runId") or "")):
        raise PreviewControlError("LAUNCH_CONFIG_INVALID", "launch run ID is invalid")
    if not isinstance(value.get("sshKeyId"), int) or value["sshKeyId"] < 1:
        raise PreviewControlError("LAUNCH_CONFIG_INVALID", "launch SSH key ID is invalid")
    if not isinstance(value.get("ttlMinutes"), int) or not 10 <= value["ttlMinutes"] <= 60:
        raise PreviewControlError("LAUNCH_CONFIG_INVALID", "launch TTL is outside policy")
    for field in LAUNCH_FIELDS - {"schemaVersion", "sshKeyId", "ttlMinutes"}:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise PreviewControlError("LAUNCH_CONFIG_INVALID", f"launch field is invalid: {field}")
    return value


def launch_from_config(
    value: dict,
    *,
    runner: Callable = subprocess.run,
    timer_runner: Callable = subprocess.run,
    provider_factory: Callable = DigitalOceanHttpClient,
) -> dict:
    config = validate_launch_config(value)
    repo = Path(config["repoRoot"]).resolve(strict=True)
    inspect_runtime(repo)
    if Path(config["pythonExecutable"]).resolve(strict=True) != Path(sys.executable).resolve(
        strict=True
    ):
        raise PreviewControlError(
            "LAUNCH_CONFIG_INVALID", "launch must use the admitted control-plane Python"
        )
    commit = prove_exact_main(repo, runner=runner)
    state_root = admit_private_root(config["stateRoot"], create=True)
    lease_inventory = inventory(state_root)
    source_dir = Path(config["sourceArchiveDir"])
    source_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if source_dir.is_symlink() or stat.S_IMODE(source_dir.stat().st_mode) & 0o077:
        raise PreviewControlError("LAUNCH_CONFIG_INVALID", "source archive directory is invalid")
    archive = source_dir / f"base2-{commit}.tar"
    archived = runner(
        ["git", "archive", "--format=tar", f"--output={archive}", commit],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if archived.returncode != 0:
        raise PreviewControlError("SOURCE_NOT_EXACT_MAIN", "deterministic source archive failed")
    archive.chmod(0o600)
    profile = Path(config["profilePath"]).resolve(strict=True)
    expected_profile = (repo / "site_profiles/base2-obsidian.json").resolve(strict=True)
    if profile != expected_profile:
        raise PreviewControlError(
            "LAUNCH_CONFIG_INVALID", "launch profile is outside the fixed Base2 profile"
        )
    profile_digest = hashlib.sha256(profile.read_bytes()).hexdigest()
    provider = provider_factory(_token(Path(config["credentialFile"])))
    provider_receipt = reconcile_provider_inventory(provider.droplets, lease_inventory)
    if not provider_receipt["ok"]:
        raise PreviewControlError("LEASE_CONFLICT", "exact-owned preview inventory is not empty")
    intent_root = state_root / "intents"
    intent_root.mkdir(mode=0o700, exist_ok=True)
    intent = {
        "schemaVersion": 1,
        "runId": config["runId"],
        "sourceCommit": commit,
        "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "configDigest": _digest({k: v for k, v in config.items() if k not in {"credentialFile"}}),
        "state": "launch-pending",
        "secretValuesEmitted": 0,
    }
    intent_path = intent_root / f"{config['runId']}.json"
    intent_path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    intent_path.chmod(0o600)
    args = [
        config["pythonExecutable"],
        "-m",
        "digital_ocean.scripts.python.full_preview_live",
        "--credential-file",
        config["credentialFile"],
        "--source-archive",
        str(archive),
        "--ssh-private-key",
        config["sshPrivateKey"],
        "--ssh-key-id",
        str(config["sshKeyId"]),
        "--operator-auth-file",
        config["operatorAuthFile"],
        "--flower-auth-file",
        config["flowerAuthFile"],
        "--probe-username-file",
        config["probeUsernameFile"],
        "--probe-password-file",
        config["probePasswordFile"],
        "--django-username-file",
        config["djangoUsernameFile"],
        "--django-email-file",
        config["djangoEmailFile"],
        "--django-password-file",
        config["djangoPasswordFile"],
        "--pgadmin-email-file",
        config["pgadminEmailFile"],
        "--pgadmin-password-file",
        config["pgadminPasswordFile"],
        "--source-commit",
        commit,
        "--profile-digest",
        profile_digest,
        "--domain",
        config["domain"],
        "--owner-cidr",
        config["ownerCidr"],
        "--run-id",
        config["runId"],
        "--state-root",
        str(state_root / config["runId"]),
        "--ttl-minutes",
        str(config["ttlMinutes"]),
    ]
    launched = _run_json(args, cwd=repo, runner=runner)
    intent["state"] = "live-awaiting-expiry"
    intent_path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        plan = build_expiry_plan(
            lease_root=state_root / config["runId"] / "leases",
            run_id=config["runId"],
            credential_file=config["credentialFile"],
            python_executable=config["pythonExecutable"],
            repo_root=repo,
        )
        armed = arm_expiry(plan, runner=timer_runner)
    except Exception as exc:
        cleanup_args = [
            config["pythonExecutable"],
            "-m",
            "digital_ocean.scripts.python.full_preview_expire",
            "--state-root",
            str(state_root / config["runId"] / "leases"),
            "--run-id",
            config["runId"],
            "--credential-file",
            config["credentialFile"],
            "--early-approved",
        ]
        try:
            cleanup = _run_json(cleanup_args, cwd=repo, runner=runner)
        except Exception as cleanup_exc:
            raise PreviewControlError(
                "CLEANUP_RECONCILIATION_REQUIRED",
                "expiry arming and exact cleanup failed",
                cleanup_state="reconciliation-required",
            ) from cleanup_exc
        raise PreviewControlError(
            "EXPIRY_NOT_ARMED",
            "expiry arming failed and exact cleanup completed",
            cleanup_state=cleanup.get("state", "destroyed"),
        ) from exc
    intent["state"] = "live-bounded"
    intent["expiryPlanDigest"] = plan["planDigest"]
    intent_path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "launch": launched,
        "expiry": armed,
        "prelaunchInventory": provider_receipt,
        "intentDigest": _digest(intent),
        "budgetCeilingUsd": "0.25",
        "estimatedMaximumCostUsd": "0.025",
        "secretValuesEmitted": 0,
    }


def _outbox(state_root: Path | None, receipt: dict) -> None:
    if state_root is None or receipt["ok"]:
        return
    try:
        root = admit_private_root(state_root, create=True) / "outbox"
        root.mkdir(mode=0o700, exist_ok=True)
        identifier = receipt["requestDigest"][:20]
        payload = {
            "schemaVersion": 1,
            "code": receipt["code"],
            "summary": receipt["summary"],
            "cleanupState": receipt["cleanupState"],
            "recommendedAction": receipt["recommendedAction"],
            "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "secretValuesEmitted": 0,
        }
        path = root / f"failure-{identifier}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)
    except Exception:
        return


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--repo", required=True)
    status = sub.add_parser("status")
    status.add_argument("--state-root", required=True)
    provider_status = sub.add_parser("provider-status")
    provider_status.add_argument("--state-root", required=True)
    provider_status.add_argument("--credential-file", required=True)
    dns = sub.add_parser("dns")
    dns.add_argument("--observation", required=True)
    evidence = sub.add_parser("evidence")
    evidence.add_argument("--evidence-root", required=True)
    evidence.add_argument("--commit", required=True)
    evidence.add_argument("--profile-digest", required=True)
    evidence.add_argument("--run-id", required=True)
    arm = sub.add_parser("arm-expiry")
    arm.add_argument("--lease-root", required=True)
    arm.add_argument("--run-id", required=True)
    arm.add_argument("--credential-file", required=True)
    arm.add_argument("--python-executable", required=True)
    arm.add_argument("--repo-root", required=True)
    arm.add_argument("--install", action="store_true")
    extend = sub.add_parser("extend")
    extend.add_argument("--lease-root", required=True)
    extend.add_argument("--run-id", required=True)
    extend.add_argument("--minutes", type=int, required=True)
    extend.add_argument("--credential-file", required=True)
    extend.add_argument("--python-executable", required=True)
    extend.add_argument("--repo-root", required=True)
    destroy = sub.add_parser("destroy")
    destroy.add_argument("--state-root", required=True)
    destroy.add_argument("--run-id", required=True)
    destroy.add_argument("--credential-file", required=True)
    destroy.add_argument("--early-approved", action="store_true")
    launch = sub.add_parser("launch")
    launch.add_argument("--config", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--state-root", required=True)
    verify.add_argument("--run-id", required=True)
    retention = sub.add_parser("retention")
    retention.add_argument("--state-root", required=True)
    retention.add_argument("--apply", action="store_true")
    return parser


def execute(args: argparse.Namespace) -> tuple[dict, int]:
    command = args.command
    state_root: Path | None = (
        Path(getattr(args, "state_root", "")) if getattr(args, "state_root", "") else None
    )
    try:
        if command == "preflight":
            details = inspect_runtime(args.repo)
        elif command == "status":
            details = inventory(args.state_root)
        elif command == "provider-status":
            lease_inventory = inventory(args.state_root)
            client = DigitalOceanHttpClient(_token(Path(args.credential_file)))
            details = reconcile_provider_inventory(client.droplets, lease_inventory)
        elif command == "dns":
            details = classify_dns_observation(
                _private_json(args.observation, code="DNS_OBSERVATION_INVALID")
            )
        elif command == "evidence":
            details = build_visual_bundle(
                evidence_root=args.evidence_root,
                commit=args.commit,
                profile_digest=args.profile_digest,
                run_id=args.run_id,
            )
        elif command == "arm-expiry":
            plan = build_expiry_plan(
                lease_root=args.lease_root,
                run_id=args.run_id,
                credential_file=args.credential_file,
                python_executable=args.python_executable,
                repo_root=args.repo_root,
            )
            details = arm_expiry(plan) if args.install else plan
        elif command == "extend":
            with mutation_lock(Path(args.lease_root).parent.parent):
                extension = extend_lease(
                    lease_root=args.lease_root, run_id=args.run_id, minutes=args.minutes
                )
                plan = build_expiry_plan(
                    lease_root=args.lease_root,
                    run_id=args.run_id,
                    credential_file=args.credential_file,
                    python_executable=args.python_executable,
                    repo_root=args.repo_root,
                )
                subprocess.run(
                    ["systemctl", "--user", "stop", plan["unit"] + ".timer"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                armed = arm_expiry(plan)
                details = {"extension": extension, "expiry": armed, "secretValuesEmitted": 0}
        elif command == "destroy":
            with mutation_lock(args.state_root):
                call = [
                    sys.executable,
                    "-m",
                    "digital_ocean.scripts.python.full_preview_expire",
                    "--state-root",
                    str(Path(args.state_root) / args.run_id / "leases"),
                    "--run-id",
                    args.run_id,
                    "--credential-file",
                    args.credential_file,
                ]
                if args.early_approved:
                    call.append("--early-approved")
                teardown = _run_json(call, cwd=Path.cwd())
                lease_inventory = inventory(args.state_root)
                client = DigitalOceanHttpClient(_token(Path(args.credential_file)))
                provider_receipt = reconcile_provider_inventory(client.droplets, lease_inventory)
                if not provider_receipt["ok"]:
                    raise PreviewControlError(
                        "CLEANUP_RECONCILIATION_REQUIRED",
                        "owned provider resources remain",
                        cleanup_state="reconciliation-required",
                    )
                details = {
                    "teardown": teardown,
                    "providerInventory": provider_receipt,
                    "secretValuesEmitted": 0,
                }
        elif command == "launch":
            config = _private_json(args.config, code="LAUNCH_CONFIG_INVALID")
            state_root = Path(str(config.get("stateRoot") or ""))
            with mutation_lock(state_root):
                details = launch_from_config(config)
        elif command == "verify":
            all_state = inventory(args.state_root)
            matches = [row for row in all_state["leases"] if row["runId"] == args.run_id]
            if len(matches) != 1:
                raise PreviewControlError(
                    "LEASE_INTEGRITY_INVALID", "exact run lease is unavailable"
                )
            details = {
                "lease": matches[0],
                "exactAddressBrowserTarget": matches[0]["exactAddress"],
                "publicDnsVerificationRequiredSeparately": True,
                "inventoryCode": all_state["code"],
                "secretValuesEmitted": 0,
            }
        elif command == "retention":
            with mutation_lock(args.state_root) if args.apply else nullcontext():
                details = cleanup_visual_evidence(args.state_root, apply=args.apply)
        else:
            raise PreviewControlError("LIFECYCLE_EXTERNAL_FAILURE", "unknown command")
        code = details.get("code", "OK") if isinstance(details, dict) else "OK"
        ok = bool(details.get("ok", True)) if isinstance(details, dict) else True
        receipt = _receipt(
            command,
            ok=ok,
            code=code,
            details=details,
            summary="operation completed" if ok else "operation reported findings",
        )
        _outbox(state_root, receipt)
        return receipt, EXIT_CODES.get(code, 4 if not ok else 0)
    except (
        PreviewControlError,
        RuntimeAdmissionError,
        InventoryError,
        DnsConvergenceError,
        ExpiryPlanError,
        VisualEvidenceError,
        ProviderInventoryError,
        RetentionError,
    ) as exc:
        code = getattr(exc, "code", "LIFECYCLE_EXTERNAL_FAILURE")
        cleanup = getattr(exc, "cleanup_state", "not-required")
        receipt = _receipt(
            command, ok=False, code=code, details={}, summary=str(exc), cleanup_state=cleanup
        )
        _outbox(state_root, receipt)
        return receipt, EXIT_CODES.get(code, 5)
    except Exception:
        receipt = _receipt(
            command,
            ok=False,
            code="LIFECYCLE_EXTERNAL_FAILURE",
            details={},
            summary="unexpected bounded operation failure",
            cleanup_state="unknown",
        )
        _outbox(state_root, receipt)
        return receipt, 5


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt, exit_code = execute(args)
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
