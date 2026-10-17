"""Explicit private Resend handoff for one owner-approved bounded preview."""

import argparse
import json
import math
import os
import re
import stat
import time
from pathlib import Path


def load_trial(path: Path, domain: str, *, now=None, ttl_minutes=60):
    now = time.time() if now is None else now
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise RuntimeError("mail_trial_private_input_invalid") from None
    with os.fdopen(fd, encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or info.st_size > 4096
        ):
            raise RuntimeError("mail_trial_private_input_invalid")
        data = json.load(stream)
    if not isinstance(data, dict) or set(data) != {
        "domain",
        "apiKey",
        "fromAddress",
        "recipient",
        "expiresAt",
        "maxAttempts",
    }:
        raise RuntimeError("mail_trial_schema_invalid")
    if (
        domain != "woodkilldev.com"
        or data["domain"] != domain
        or data["recipient"] != "thejunkmailvoid@gmail.com"
        or not isinstance(data["fromAddress"], str)
        or not re.fullmatch(r"[A-Za-z0-9._+-]+@woodkilldev\.com", data["fromAddress"])
        or not isinstance(data["apiKey"], str)
        or not re.fullmatch(r"re_[A-Za-z0-9_-]+", data["apiKey"])
        or type(data["maxAttempts"]) is not int
        or not 1 <= data["maxAttempts"] <= 5
        or type(data["expiresAt"]) not in {int, float}
        or not math.isfinite(data["expiresAt"])
        or type(ttl_minutes) is not int
        or not 1 <= ttl_minutes <= 60
        or not now < data["expiresAt"] <= now + ttl_minutes * 60
    ):
        raise RuntimeError("mail_trial_scope_or_expiry_invalid")
    return data


def configure_trial(source, env_path, root, domain, *, uid=1000, now=None):
    data = load_trial(source, domain, now=now)
    if root.exists() or root.is_symlink():
        raise RuntimeError("mail_trial_budget_already_exists")
    if env_path.is_symlink() or not env_path.is_file():
        raise RuntimeError("mail_trial_env_invalid")
    text = env_path.read_text()
    root.mkdir(mode=0o700)
    # Creation is exclusive: an interrupted run must be reconciled, never reset.
    key, budget = root / "key", root / "budget.json"
    for path, content in (
        (key, data["apiKey"]),
        (
            budget,
            json.dumps(
                {
                    "schemaVersion": 1,
                    "expiresAt": data["expiresAt"],
                    "maxAttempts": data["maxAttempts"],
                    "reservations": [],
                }
            ),
        ),
    ):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(path, uid, -1)
    os.chown(root, uid, -1)
    overrides = {
        "BASE2_EMAIL_ADAPTER": "resend",
        "BASE2_EMAIL_FROM_ADDRESS": data["fromAddress"],
        "BASE2_EMAIL_ALLOWED_RECIPIENTS": data["recipient"],
        "BASE2_EMAIL_RESEND_API_KEY_FILE_HOST": str(key),
        "BASE2_EMAIL_BUDGET_FILE_HOST": str(budget),
    }
    lines = [line for line in text.splitlines() if line.partition("=")[0] not in overrides]
    lines += [f"{key}={value}" for key, value in overrides.items()]
    temporary = env_path.with_suffix(".mail-trial.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write("\n".join(lines) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, env_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()
    try:
        configure_trial(args.input, args.env_file, args.state_root, args.domain)
    except Exception:
        raise SystemExit("mail_trial_configuration_failed") from None
    args.input.unlink()
    print('{"ok":true,"secretValuesEmitted":0}')


if __name__ == "__main__":
    main()
