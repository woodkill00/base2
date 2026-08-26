#!/usr/bin/env python3
"""Validate and index private Base2 live visual evidence."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import stat
import struct
from pathlib import Path

RUN_ID = re.compile(r"^base2-full-[0-9]{8}-[0-9]{6}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_ARTIFACT_BYTES = 20 * 1024 * 1024
MAX_DIMENSION = 24_000

REQUIRED_FILES = {
    "base2-live-home.png",
    "admin.png",
    "swagger.png",
    "traefik.png",
    "pgadmin.png",
    "flower.png",
    "django-authenticated.png",
    "pgadmin-authenticated.png",
}
AREAS = (
    "home-top",
    "about-top",
    "operations-top",
    "projects-top",
    "contact-top",
    "monitoring-top",
    "footer-top",
    "command-palette",
)
VIEWPORTS = ("desktop", "tablet", "mobile")


class VisualEvidenceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise VisualEvidenceError("EVIDENCE_INVALID", f"invalid PNG: {path.name}")
    width, height = struct.unpack(">II", header[16:24])
    if not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION:
        raise VisualEvidenceError("EVIDENCE_INVALID", f"PNG dimensions are invalid: {path.name}")
    return width, height


def _private_directory(root: str | os.PathLike[str]) -> Path:
    path = Path(root)
    if path.is_symlink() or not path.is_dir():
        raise VisualEvidenceError("EVIDENCE_INVALID", "evidence root must be a real directory")
    resolved = path.resolve(strict=True)
    ancestor = resolved
    protected = False
    while ancestor != ancestor.parent:
        if stat.S_IMODE(ancestor.stat().st_mode) & 0o077 == 0:
            protected = True
            break
        ancestor = ancestor.parent
    if not protected:
        raise VisualEvidenceError("EVIDENCE_INVALID", "evidence must have an owner-only ancestor")
    return resolved


def _required_names() -> set[str]:
    names = set(REQUIRED_FILES)
    for viewport in VIEWPORTS:
        for area in AREAS:
            names.add(f"public-{viewport}-{area}.png")
    return names


def _review(root: Path) -> dict:
    path = root / "visual-review.json"
    if not path.exists():
        return {"state": "pending", "feedback": "", "reviewer": None}
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
        raise VisualEvidenceError("EVIDENCE_INVALID", "visual review sidecar is invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VisualEvidenceError(
            "EVIDENCE_INVALID", "visual review sidecar is unreadable"
        ) from exc
    if not isinstance(value, dict) or set(value) != {"state", "feedback", "reviewer"}:
        raise VisualEvidenceError("EVIDENCE_INVALID", "visual review sidecar shape is invalid")
    if value["state"] not in {"pending", "approved", "rejected"}:
        raise VisualEvidenceError("EVIDENCE_INVALID", "visual review state is invalid")
    if not isinstance(value["feedback"], str) or len(value["feedback"]) > 4000:
        raise VisualEvidenceError("EVIDENCE_INVALID", "visual review feedback is invalid")
    if value["reviewer"] is not None and (
        not isinstance(value["reviewer"], str) or len(value["reviewer"]) > 100
    ):
        raise VisualEvidenceError("EVIDENCE_INVALID", "visual reviewer is invalid")
    return value


def _artifact_context(identity: str) -> dict:
    public = re.fullmatch(r"public-(desktop|tablet|mobile)-(.+)", identity)
    if public:
        return {
            "viewport": public.group(1),
            "browser": "chromium",
            "route": "/",
            "state": public.group(2),
        }
    routes = {
        "admin": "https://admin.woodkilldev.com/admin",
        "swagger": "https://swagger.woodkilldev.com/docs",
        "traefik": "https://traefik.woodkilldev.com/",
        "pgadmin": "https://pgadmin.woodkilldev.com/",
        "flower": "https://flower.woodkilldev.com/",
        "django-authenticated": "https://admin.woodkilldev.com/admin",
        "pgadmin-authenticated": "https://pgadmin.woodkilldev.com/",
        "base2-live-home": "https://woodkilldev.com/",
    }
    return {
        "viewport": "desktop",
        "browser": "chromium",
        "route": routes.get(identity, "unknown"),
        "state": "authenticated" if identity.endswith("-authenticated") else "public",
    }


def build_visual_bundle(
    *,
    evidence_root: str | os.PathLike[str],
    commit: str,
    profile_digest: str,
    run_id: str,
    write: bool = True,
) -> dict:
    root = _private_directory(evidence_root)
    if (
        not SHA.fullmatch(commit)
        or not SHA256.fullmatch(profile_digest)
        or not RUN_ID.fullmatch(run_id)
    ):
        raise VisualEvidenceError("EVIDENCE_INVALID", "evidence binding is invalid")
    artifacts = []
    identities = set()
    for path in sorted(root.rglob("*.png"), key=lambda item: str(item.relative_to(root))):
        relative = path.relative_to(root)
        if path.is_symlink() or any(
            parent.is_symlink() for parent in path.parents if parent != root.parent
        ):
            raise VisualEvidenceError("EVIDENCE_INVALID", "evidence symlink is forbidden")
        if len(relative.parts) != 1:
            continue
        size = path.stat().st_size
        if size > MAX_ARTIFACT_BYTES:
            raise VisualEvidenceError(
                "EVIDENCE_INVALID", f"evidence artifact is oversized: {path.name}"
            )
        identity = path.stem
        if identity in identities:
            raise VisualEvidenceError("EVIDENCE_INVALID", "duplicate visual identity")
        identities.add(identity)
        width, height = _png_dimensions(path)
        artifacts.append(
            {
                "identity": identity,
                "path": path.name,
                "mediaType": "image/png",
                "size": size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
                "reviewState": "pending",
                **_artifact_context(identity),
            }
        )
    present = {row["path"] for row in artifacts}
    missing = sorted(_required_names() - present)
    review = _review(root)
    for artifact in artifacts:
        artifact["reviewState"] = review["state"]
    bundle = {
        "schemaVersion": 1,
        "ok": not missing,
        "code": "OK" if not missing else "EVIDENCE_INCOMPLETE",
        "runId": run_id,
        "sourceCommit": commit,
        "profileDigest": profile_digest,
        "artifactCount": len(artifacts),
        "artifacts": artifacts,
        "missing": missing,
        "review": review,
        "secretValuesEmitted": 0,
    }
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    bundle["bundleDigest"] = hashlib.sha256(canonical).hexdigest()
    if write:
        manifest = root / "visual-evidence.json"
        manifest.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.chmod(0o600)
        cards = "\n".join(
            f'<article><img src="{html.escape(row["path"])}" alt="{html.escape(row["identity"])}">'
            f'<h2>{html.escape(row["identity"])}</h2><code>{row["sha256"]}</code></article>'
            for row in artifacts
        )
        page = (
            "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width,initial-scale=1\"><title>Base2 visual evidence</title>"
            "<style>body{background:#090909;color:#eee;font:14px system-ui;margin:2rem}main{display:grid;"
            "grid-template-columns:repeat(auto-fit,minmax(min(100%,22rem),1fr));gap:1rem}article{border:1px solid #5b2018;"
            "padding:1rem;background:#111}img{display:block;max-width:100%;height:auto}code{overflow-wrap:anywhere}</style>"
            f"</head><body><h1>Base2 visual evidence</h1><p>Run {html.escape(run_id)} · {len(artifacts)} artifacts · "
            f"review {html.escape(review['state'])}</p><main>{cards}</main></body></html>"
        )
        index = root / "visual-evidence.html"
        index.write_text(page, encoding="utf-8")
        index.chmod(0o600)
    return bundle
