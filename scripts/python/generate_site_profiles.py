#!/usr/bin/env python3
"""Generate integrity-bound, service-local site profiles from canonical manifests."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.python.site_manifest import load_manifest, manifest_digest  # noqa: E402

TARGETS = (
    ROOT / "api" / "site_profiles",
    ROOT / "django" / "site_profiles",
    ROOT / "react-app" / "src" / "config" / "generated",
)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def generate(*, check: bool = False) -> dict[str, str]:
    profiles: dict[str, dict] = {}
    digests: dict[str, str] = {}
    for source in sorted((ROOT / "site_profiles").glob("*.json")):
        payload = load_manifest(source)
        profile_id = payload["siteId"]
        if source.stem != profile_id:
            raise ValueError(f"profile filename must equal siteId: {source.name}")
        profiles[profile_id] = payload
        digests[profile_id] = manifest_digest(payload)
    if not profiles:
        raise ValueError("at least one canonical site profile is required")

    outputs: dict[Path, str] = {}
    index = (
        json.dumps(
            {"schemaVersion": 1, "defaultProfile": "ember-studio", "profiles": digests},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    if "ember-studio" not in profiles:
        raise ValueError("compatibility default ember-studio is missing")
    for target in TARGETS:
        outputs[target / "index.json"] = index
        for profile_id, payload in profiles.items():
            outputs[target / f"{profile_id}.json"] = (
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            )

    stale: list[str] = []
    expected = set(outputs)
    for target in TARGETS:
        if target.exists():
            for path in target.glob("*.json"):
                if path not in expected:
                    stale.append(str(path.relative_to(ROOT)))
    for path, content in outputs.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(str(path.relative_to(ROOT)))
            if not check:
                _atomic_write(path, content)
    if check and stale:
        raise ValueError("generated site profiles are stale: " + ", ".join(sorted(set(stale))))
    return digests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    digests = generate(check=args.check)
    print(json.dumps({"status": "current", "profiles": digests}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
