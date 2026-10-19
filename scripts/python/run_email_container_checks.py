"""Network-isolated, synthetic mail-worker filesystem/restart acceptance."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

PHASES = (
    "first",
    "restart",
    "second",
    "exhausted",
    "expired",
    "corrupt",
    "public-key",
    "public-budget",
    "hardlink-key",
    "hardlink-budget",
)


def run_phase(command, name, phase):
    """Bound execution and remove only this invocation's container, even on timeout."""
    failed = True
    try:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=45, check=False
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("email_container_check_timeout_" + phase) from None
        if result.returncode != 0:
            raise RuntimeError("email_container_check_failed_" + phase)
        try:
            payload = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise RuntimeError("email_container_receipt_invalid") from None
        if payload != {"ok": True, "phase": phase, "externalRequests": 0}:
            raise RuntimeError("email_container_receipt_invalid")
        failed = False
    finally:
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            cleanup_failed = cleanup.returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            cleanup_failed = True
        if cleanup_failed:
            print("email_container_cleanup_failed", file=sys.stderr)
            if not failed:
                raise RuntimeError("email_container_cleanup_failed") from None


def inside(phase):
    import httpx

    from api.services.email_service import _configured_adapter
    from api.services.transactional_email import RenderedEmail

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "synthetic-message"})

    os.environ.update(
        {
            "BASE2_EMAIL_ADAPTER": "resend",
            "BASE2_EMAIL_RESEND_API_KEY_FILE": "/trial/key",
            "BASE2_EMAIL_FROM_ADDRESS": "sender@example.com",
            "BASE2_EMAIL_ALLOWED_RECIPIENTS": "owner@example.com",
            "BASE2_EMAIL_BUDGET_FILE": "/trial/budget.json",
        }
    )
    expected = {
        "restart": "email_budget_duplicate_requires_reconciliation",
        "exhausted": "email_budget_exhausted",
        "expired": "email_budget_expired_or_invalid",
        "corrupt": "email_budget_unavailable_or_corrupt",
        "public-key": "email_secret_file_permissions",
        "public-budget": "email_budget_file_unsafe",
        "hardlink-key": "email_secret_file_permissions",
        "hardlink-budget": "email_budget_file_unsafe",
    }
    message = RenderedEmail(
        "verification",
        "owner@example.com",
        "Synthetic",
        "fixture",
        "",
        "stable-key" if phase in ("first", "restart") else "key-" + phase,
    )
    try:
        mailer = _configured_adapter()
        mailer._transport = httpx.MockTransport(handler)
        result = mailer.send(message)
    except RuntimeError as exc:
        assert phase in expected and str(exc) == expected[phase]
        assert calls == []
    else:
        assert phase in ("first", "second"), "guard_did_not_block"
        assert result.status == "sent" and len(calls) == 1
    print(json.dumps({"ok": True, "phase": phase, "externalRequests": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", choices=PHASES)
    parser.add_argument("--image", default="base2-e2e-isolated-api:latest")
    args = parser.parse_args()
    if args.inside:
        inside(args.inside)
        return
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo))
    from digital_ocean.scripts.python.mail_trial_config import configure_trial

    with tempfile.TemporaryDirectory(prefix="base2-mail-synthetic-") as directory:
        scratch = Path(directory)
        root = scratch / "state"
        source, env = scratch / "input.json", scratch / ".env"
        source.write_text(
            json.dumps(
                {
                    "domain": "woodkilldev.com",
                    "apiKey": "re_synthetic_not_a_credential",
                    "fromAddress": "noreply@woodkilldev.com",
                    "recipient": "thejunkmailvoid+base2-test@gmail.com",
                    "expiresAt": time.time() + 600,
                    "maxAttempts": 2,
                }
            )
        )
        source.chmod(0o600)
        env.write_text("UNRELATED=preserved\n")
        configure_trial(source, env, root, "woodkilldev.com", uid=os.getuid())
        budget = root / "budget.json"
        key = root / "key"
        for path in (key, budget):
            assert path.stat().st_uid == os.getuid() and path.stat().st_mode & 0o777 == 0o600
        for phase in PHASES:
            if phase == "restart":
                before = {path: path.read_bytes() for path in (key, budget, env)}
                try:
                    configure_trial(source, env, root, "woodkilldev.com", uid=os.getuid())
                except RuntimeError as exc:
                    assert str(exc) == "mail_trial_budget_already_exists"
                else:
                    raise AssertionError("mail_trial_budget_reset_allowed")
                assert all(path.read_bytes() == value for path, value in before.items())
            if phase == "expired":
                state = json.loads(budget.read_text())
                state["expiresAt"] = time.time() - 1
                budget.write_text(json.dumps(state))
            if phase == "corrupt":
                budget.write_text("interrupted-write")
            if phase == "public-key":
                key.chmod(0o644)
            if phase == "public-budget":
                key.chmod(0o600)
                budget.chmod(0o644)
            if phase == "hardlink-key":
                budget.chmod(0o600)
                (root / "key-link").hardlink_to(key)
            if phase == "hardlink-budget":
                (root / "key-link").unlink()
                (root / "budget-link").hardlink_to(budget)
            name = "base2-mail-check-" + uuid.uuid4().hex
            command = [
                "docker",
                "run",
                "--name",
                name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--tmpfs",
                "/tmp:size=32m",
                "--mount",
                f'type=bind,src={repo / "api"},dst=/app/api,readonly',
                "--mount",
                f"type=bind,src={Path(__file__).resolve()},dst=/checks/check.py,readonly",
                "--mount",
                f"type=bind,src={root},dst=/trial",
                "--entrypoint",
                "python",
                args.image,
                "/checks/check.py",
                "--inside",
                phase,
            ]
            run_phase(command, name, phase)
    print(
        json.dumps(
            {
                "ok": True,
                "phases": list(PHASES),
                "externalRequests": 0,
                "scope": "synthetic_transport_not_full_stack",
            }
        )
    )


if __name__ == "__main__":
    main()
