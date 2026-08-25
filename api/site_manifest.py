"""Integrity-bound runtime access to generated site profiles."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

PROFILE_ID = re.compile(r'^[a-z][a-z0-9-]{2,62}$')
ROOT = Path(__file__).resolve().parent / 'site_profiles'


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_runtime_manifest(profile_id: str | None = None) -> tuple[dict[str, Any], str]:
    index = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    selected = (profile_id or os.getenv('SITE_PROFILE') or index['defaultProfile']).strip()
    if not PROFILE_ID.fullmatch(selected) or selected not in index['profiles']:
        raise RuntimeError('SITE_PROFILE is not an allowed generated profile')
    path = ROOT / f'{selected}.json'
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('generated site profile must be a real file')
    payload = json.loads(path.read_text(encoding='utf-8'))
    digest = _canonical_digest(payload)
    if digest != index['profiles'][selected] or payload.get('siteId') != selected:
        raise RuntimeError('generated site profile failed integrity verification')
    return payload, digest
