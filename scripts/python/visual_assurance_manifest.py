#!/usr/bin/env python3
"""Build deterministic, integrity-bound Base2 visual assurance evidence."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = "react-app/e2e/visual"
MAX_MEMBER_BYTES = 8 * 1024 * 1024
PROJECT = re.compile(r"-(desktop|tablet|mobile)-linux\.png$")
ROUTES = (
    {"id": "public", "path": "/", "host": "woodkilldev.com", "auth": "public", "hermetic": True},
    {"id": "admin", "path": "/admin", "host": "admin.woodkilldev.com", "auth": "edge+django+csrf", "hermetic": False},
    {"id": "api", "path": "/api", "host": "woodkilldev.com", "auth": "edge+api", "hermetic": False},
    {"id": "swagger", "path": "/docs", "host": "swagger.woodkilldev.com", "auth": "edge", "hermetic": False},
    {"id": "pgadmin", "path": "/", "host": "pgadmin.woodkilldev.com", "auth": "edge+pgadmin", "hermetic": False},
    {"id": "traefik", "path": "/", "host": "traefik.woodkilldev.com", "auth": "edge", "hermetic": False},
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def tracked(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", SNAPSHOT_ROOT], cwd=root,
        capture_output=True, check=True,
    )
    return sorted(item.decode() for item in result.stdout.split(b"\0") if item)


def source_commit(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{40}", result):
        raise ValueError("source commit invalid")
    return result


def build(root: Path = ROOT, *, commit: str | None = None) -> dict:
    members = []
    for relative in tracked(root):
        if not relative.endswith(".png"):
            continue
        path = root / relative
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise PermissionError("visual baseline member must be a regular file")
        if not 8 <= info.st_size <= MAX_MEMBER_BYTES:
            raise ValueError("visual baseline member size invalid")
        raw = path.read_bytes()
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("visual baseline member is not PNG")
        match = PROJECT.search(relative)
        project = match.group(1) if match else "shared"
        members.append({
            "path": relative,
            "size": len(raw),
            "sha256": sha256(raw),
            "project": project,
            "routeClass": "public",
            "area": Path(relative).name.rsplit("-", 2)[0],
        })
    if not members or len({row["path"] for row in members}) != len(members):
        raise ValueError("visual baseline inventory missing or duplicated")
    payload = {
        "schemaVersion": 1,
        "sourceCommit": commit or source_commit(root),
        "baselineCount": len(members),
        "projects": sorted({row["project"] for row in members}),
        "routes": list(ROUTES),
        "members": members,
        "claims": {
            "hermeticPublicVisualProof": True,
            "liveProtectedRouteProofRequired": True,
            "externalAssetsAllowed": False,
            "productionCertificatesAllowed": False,
        },
    }
    payload["inventoryDigest"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return payload


def validate(payload: dict) -> None:
    claimed = payload.get("inventoryDigest")
    unsigned = {key: value for key, value in payload.items() if key != "inventoryDigest"}
    if claimed != sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()):
        raise ValueError("visual inventory digest invalid")
    members = payload.get("members")
    if not isinstance(members, list) or payload.get("baselineCount") != len(members):
        raise ValueError("visual inventory count invalid")
    if len({row.get("path") for row in members}) != len(members):
        raise ValueError("visual inventory duplicate member")
    if {row.get("id") for row in payload.get("routes", [])} != {row["id"] for row in ROUTES}:
        raise ValueError("visual route classes incomplete")


def render_markdown(payload: dict) -> str:
    validate(payload)
    routes = "\n".join(
        f"| {row['id']} | `{row['host']}{row['path']}` | {row['auth']} | "
        f"{'hermetic' if row['hermetic'] else 'live approval required'} |"
        for row in payload["routes"]
    )
    return (
        "# Generated visual assurance manifest\n\n"
        f"Source: `{payload['sourceCommit']}`  \n"
        f"Baselines: {payload['baselineCount']}  \n"
        f"Inventory SHA-256: `{payload['inventoryDigest']}`\n\n"
        "| Route class | Target | Authentication | Proof boundary |\n"
        "|---|---|---|---|\n" + routes + "\n\n"
        "Protected-route rows are contracts, not claims of live availability. "
        "Live proof requires a separately approved ephemeral preview.\n"
    )


def export(payload: dict, destination: Path) -> dict:
    validate(payload)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    raw = json.dumps(payload, indent=2, sort_keys=True).encode() + b"\n"
    page = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">"
        "<meta http-equiv='Cache-Control' content='no-store'><meta name='referrer' content='no-referrer'>"
        "<title>Base2 visual assurance</title></head><body><h1>Base2 visual assurance</h1>"
        f"<p>{payload['baselineCount']} baselines · {html.escape(payload['inventoryDigest'])}</p>"
        "</body></html>"
    ).encode()
    files = {"visual-assurance.json": raw, "visual-assurance.html": page}
    for name, content in files.items():
        path = destination / name
        path.write_bytes(content); os.chmod(path, 0o600)
    manifest = {
        "version": 1, "kind": "base2-visual-assurance", "category": "reliability",
        "title": "Base2 visual assurance", "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "quality": "verified", "files": [
            {"path": name, "size": len(content), "sha256": sha256(content)}
            for name, content in sorted(files.items())
        ],
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(destination / "manifest.json", 0o600)
    return {"ok": True, "baselineCount": payload["baselineCount"], "inventoryDigest": payload["inventoryDigest"], "secretValuesEmitted": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inspect", "markdown", "export"))
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    payload = build()
    if args.command == "markdown":
        print(render_markdown(payload), end="")
    elif args.command == "export":
        if not args.destination:
            parser.error("--destination is required")
        print(json.dumps(export(payload, args.destination), sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
