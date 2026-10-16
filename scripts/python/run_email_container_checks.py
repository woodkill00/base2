"""Network-isolated, synthetic mail-worker filesystem/restart acceptance."""

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


def inside(phase):
    import httpx

    from api.services.resend_email import ResendEmailAdapter
    from api.services.transactional_email import RenderedEmail

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "synthetic-message"})

    mailer = ResendEmailAdapter(
        api_key=Path("/trial/key").read_text().strip(),
        from_address="sender@example.com",
        allowed_recipients={"owner@example.com"},
        budget_file="/trial/budget.json",
        transport=httpx.MockTransport(handler),
    )
    message = RenderedEmail(
        "verification", "owner@example.com", "Synthetic", "fixture", "", "stable-key"
    )
    if phase == "first":
        assert mailer.send(message).status == "sent"
        assert len(calls) == 1
    else:
        expected = (
            "duplicate_requires_reconciliation" if phase == "restart" else "unavailable_or_corrupt"
        )
        try:
            mailer.send(message)
        except RuntimeError as exc:
            assert str(exc) == "email_budget_" + expected
        else:
            raise AssertionError("guard_did_not_block")
        assert calls == []
    print(json.dumps({"ok": True, "phase": phase, "externalRequests": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", choices=["first", "restart", "corrupt"])
    parser.add_argument("--image", default="base2-e2e-isolated-api:latest")
    args = parser.parse_args()
    if args.inside:
        inside(args.inside)
        return
    repo = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="base2-mail-synthetic-") as directory:
        root = Path(directory)
        budget = root / "budget.json"
        budget.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "expiresAt": time.time() + 600,
                    "maxAttempts": 2,
                    "reservations": [],
                }
            )
        )
        key = root / "key"
        key.write_text("re_synthetic_not_a_credential")
        for path in (key, budget):
            path.chmod(0o600)
        for phase in ("first", "restart", "corrupt"):
            if phase == "corrupt":
                budget.write_text("interrupted-write")
            command = [
                "docker",
                "run",
                "--rm",
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
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=45, check=False
            )
            if result.returncode != 0:
                raise RuntimeError("email_container_check_failed_" + phase)
            payload = json.loads(result.stdout)
            if payload != {"ok": True, "phase": phase, "externalRequests": 0}:
                raise RuntimeError("email_container_receipt_invalid")
    print(
        json.dumps(
            {
                "ok": True,
                "phases": ["first", "restart", "corrupt"],
                "externalRequests": 0,
                "scope": "synthetic_transport_not_full_stack",
            }
        )
    )


if __name__ == "__main__":
    main()
