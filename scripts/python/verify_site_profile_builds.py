#!/usr/bin/env python3
"""Build both fixture brands from the current tree and verify selected output."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REACT = ROOT / "react-app"


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    subprocess.run(
        [
            str(ROOT / ".venv" / "bin" / "python"),
            "scripts/python/generate_site_profiles.py",
            "--check",
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    receipts: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="base2-site-builds-") as temporary:
        for profile_id in ("ember-studio", "northstar-library"):
            output = Path(temporary) / profile_id
            environment = os.environ.copy()
            environment["VITE_SITE_PROFILE"] = profile_id
            subprocess.run(
                ["npm", "run", "build", "--", "--outDir", str(output)],
                cwd=REACT,
                env=environment,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            metadata = json.loads((output / "site-profile.json").read_text(encoding="utf-8"))
            html = (output / "index.html").read_text(encoding="utf-8")
            manifest = json.loads(
                (ROOT / "site_profiles" / f"{profile_id}.json").read_text(encoding="utf-8")
            )
            canonical = next(item["host"] for item in manifest["domains"] if item["kind"] == "canonical")
            robots = "index,follow" if manifest["seo"]["indexing"] == "allow" else "noindex,nofollow"
            if metadata["siteId"] != profile_id or f'data-site-id="{profile_id}"' not in html:
                raise RuntimeError(f"built profile selection was not preserved for {profile_id}")
            expected = (
                f'<title>{manifest["name"]}</title>',
                f'content="{manifest["seo"]["description"]}"',
                f'<meta name="robots" content="{robots}"',
                f'href="https://{canonical}/"',
            )
            if any(marker not in html for marker in expected):
                raise RuntimeError(f"built brand metadata was not preserved for {profile_id}")
            receipts[profile_id] = _tree_digest(output)
    if len(set(receipts.values())) != len(receipts):
        raise RuntimeError("fixture profile builds are not distinct")
    print(json.dumps({"status": "passed", "buildDigests": receipts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
