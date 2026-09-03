#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = Path("react-app/e2e/workspace/workspace-release.spec.ts-snapshots")
SURFACES = ("records", "schema", "imports", "exports")
PROJECTS = (
    "chromium-compact",
    "chromium-phone-dpr3",
    "chromium-landscape-touch",
    "chromium-tablet",
    "chromium-desktop",
    "chromium-ultrawide",
    "chromium-large-text",
    "chromium-400-zoom",
    "chromium-light",
    "chromium-high-contrast",
    "firefox-desktop",
    "webkit-mobile",
)
MAX_BYTES = 8 * 1024 * 1024
FIXTURE_COVERAGE = {
    "fieldKinds": 18,
    "recordStates": ["draft", "in_review", "scheduled", "published", "archived", "deleted"],
    "jobStates": [
        "queued", "validating", "validated", "review_required", "committing", "completed",
        "failed", "cancelled", "expired",
    ],
    "mediaOutcomes": ["quarantined", "scanning", "validated", "rejected", "deleted"],
    "relationshipOutcomes": ["empty", "attached", "restricted-delete", "cascade-delete"],
    "errorOutcomes": [
        "authorization-denied", "conflict", "validation-failed", "network-failed",
        "polling-exhausted",
    ],
    "content": ["long", "rtl"],
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_commit(root: Path) -> str:
    value = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True
    ).stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{40}", value):
        raise ValueError("workspace_visual_commit_invalid")
    return value


def build(root: Path = ROOT, *, commit: str | None = None, review_status: str = "pending") -> dict:
    if review_status not in {"pending", "reviewed-no-findings"}:
        raise ValueError("workspace_visual_review_status_invalid")
    members = []
    for surface in SURFACES:
        for project in PROJECTS:
            relative = SNAPSHOT_ROOT / f"workspace-{surface}-{project}-{project}-linux.png"
            path = root / relative
            info = os.lstat(path)
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise PermissionError("workspace_visual_member_invalid")
            raw = path.read_bytes()
            if not 8 <= len(raw) <= MAX_BYTES or raw[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("workspace_visual_png_invalid")
            with Image.open(path) as image:
                width, height = image.size
            members.append(
                {
                    "path": relative.as_posix(),
                    "surface": surface,
                    "project": project,
                    "width": width,
                    "height": height,
                    "size": len(raw),
                    "sha256": digest(raw),
                }
            )
    payload = {
        "schemaVersion": 1,
        "sourceCommit": commit or source_commit(root),
        "route": "/workspace",
        "fixture": "synthetic-no-credentials-no-network",
        "fixtureCoverage": FIXTURE_COVERAGE,
        "surfaces": list(SURFACES),
        "projects": list(PROJECTS),
        "memberCount": len(members),
        "reviewStatus": review_status,
        "members": members,
    }
    payload["inventoryDigest"] = digest(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    )
    return payload


def validate(payload: dict) -> None:
    claimed = payload.get("inventoryDigest")
    unsigned = {key: value for key, value in payload.items() if key != "inventoryDigest"}
    if claimed != digest(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()):
        raise ValueError("workspace_visual_digest_invalid")
    expected = {(surface, project) for surface in SURFACES for project in PROJECTS}
    actual = {(row.get("surface"), row.get("project")) for row in payload.get("members", [])}
    if actual != expected or payload.get("memberCount") != len(expected):
        raise ValueError("workspace_visual_matrix_incomplete")
    if payload.get("reviewStatus") not in {"pending", "reviewed-no-findings"}:
        raise ValueError("workspace_visual_review_status_invalid")


def contact_sheet(payload: dict, root: Path, destination: Path) -> None:
    validate(payload)
    thumb_width, thumb_height = 280, 190
    sheet = Image.new("RGB", (thumb_width * 4, (thumb_height + 36) * len(PROJECTS)), "#111827")
    draw = ImageDraw.Draw(sheet)
    by_key = {(row["surface"], row["project"]): row for row in payload["members"]}
    for row_index, project in enumerate(PROJECTS):
        for column, surface in enumerate(SURFACES):
            member = by_key[(surface, project)]
            with Image.open(root / member["path"]) as source:
                source = source.convert("RGB")
                source.thumbnail((thumb_width - 8, thumb_height - 8))
                x = column * thumb_width + (thumb_width - source.width) // 2
                y = row_index * (thumb_height + 36) + 4
                sheet.paste(source, (x, y))
            draw.text(
                (column * thumb_width + 6, row_index * (thumb_height + 36) + thumb_height + 6),
                f"{project} · {surface}", fill="#f8fafc",
            )
    sheet.save(destination, format="PNG", optimize=True)


def export(payload: dict, destination: Path, root: Path = ROOT) -> dict:
    validate(payload)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    json_path = destination / "workspace-visual-assurance.json"
    review_path = destination / "workspace-visual-review.md"
    sheet_path = destination / "workspace-contact-sheet.png"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    review_path.write_text(
        "# Workspace visual review\n\n"
        f"Status: `{payload['reviewStatus']}`  \n"
        f"Source: `{payload['sourceCommit']}`  \n"
        f"Screenshots: {payload['memberCount']}  \n"
        f"Inventory: `{payload['inventoryDigest']}`\n\n"
        "Review dimensions: hierarchy, clipping, reflow, directionality, focus, target size, "
        "contrast, density, job controls, and responsive navigation.\n"
    )
    contact_sheet(payload, root, sheet_path)
    files = []
    for path in (json_path, review_path, sheet_path):
        os.chmod(path, 0o600)
        raw = path.read_bytes()
        files.append({"path": path.name, "size": len(raw), "sha256": digest(raw)})
    manifest = {
        "version": 1,
        "kind": "base2-workspace-visual-assurance",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "files": files,
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(manifest_path, 0o600)
    return {"ok": True, "memberCount": payload["memberCount"], "reviewStatus": payload["reviewStatus"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inspect", "export"))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--review-status", default="pending")
    args = parser.parse_args()
    payload = build(review_status=args.review_status)
    if args.command == "export":
        if args.destination is None:
            parser.error("--destination is required")
        print(json.dumps(export(payload, args.destination), sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
