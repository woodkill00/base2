"""Private, fixed-command fixture handoff after current preview lease validation."""

import json
import os
from pathlib import Path
import secrets
import stat
import subprocess


def provision_media_inputs(*, receipt, receipt_path: Path, ssh_key: Path, runner=subprocess.run):
    known_hosts = receipt_path.parent.parent / "known_hosts"
    for path in (ssh_key, known_hosts):
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError("fixture_private_path")
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_nlink != 1
        ):
            raise ValueError("fixture_private_file")
    password = secrets.token_urlsafe(32) + "Aa9!"
    config = {"run_id": receipt["runId"], "expires_at": receipt["expiresAt"], "password": password}
    import ipaddress

    address = str(ipaddress.IPv4Address(receipt["publicIp"]))
    result = runner(
        [
            "ssh",
            "-i",
            str(ssh_key),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={known_hosts}",
            "-o",
            "ConnectTimeout=5",
            f"root@{address}",
            "docker exec -i -e BASE2_PREVIEW_MEDIA_FIXTURE=true base2-full-preview_api python -m api.scripts.preview_media_fixture",
        ],
        input=json.dumps(config),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or len(result.stdout) > 1024:
        raise ValueError("fixture_provisioning_failed")
    if json.loads(result.stdout) != {
        "status": "created",
        "role": "editor",
        "secretValuesEmitted": 0,
    }:
        raise ValueError("fixture_receipt_invalid")
    return {
        "BASE2_MEDIA_EMAIL": f"media-{receipt['runId']}@example.invalid",
        "BASE2_MEDIA_PASSWORD": password,
    }
