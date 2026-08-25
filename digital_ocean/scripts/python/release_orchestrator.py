#!/usr/bin/env python3
"""Provider-neutral immutable release admission, observation, and rollback."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable


class ReleaseDenied(ValueError):
    pass


DIGEST = re.compile(r'^[0-9a-f]{64}$')
COMMIT = re.compile(r'^[0-9a-f]{40}$')
IMAGE = re.compile(r'^[a-z0-9][a-z0-9./_-]{2,190}@sha256:([0-9a-f]{64})$')


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def signed_release(*, release_id: str, image: str, source_commit: str, sbom_digest: str, provenance_digest: str, signing_key: bytes) -> dict[str, Any]:
    if not re.fullmatch(r'release-[A-Za-z0-9._-]{4,120}', release_id or ''):
        raise ReleaseDenied('release:id_invalid')
    if not IMAGE.fullmatch(image or ''):
        raise ReleaseDenied('release:image_not_immutable')
    if not COMMIT.fullmatch(source_commit or '') or not DIGEST.fullmatch(sbom_digest or '') or not DIGEST.fullmatch(provenance_digest or ''):
        raise ReleaseDenied('release:provenance_invalid')
    if len(signing_key) < 32:
        raise ReleaseDenied('release:signing_key_invalid')
    value = {'schemaVersion':1,'releaseId':release_id,'image':image,'sourceCommit':source_commit,'sbomDigest':sbom_digest,'provenanceDigest':provenance_digest}
    value['signature'] = hmac.new(signing_key, _canonical(value), hashlib.sha256).hexdigest()
    return value


def verify_release(value: Any, *, signing_key: bytes) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {'schemaVersion','releaseId','image','sourceCommit','sbomDigest','provenanceDigest','signature'}:
        raise ReleaseDenied('release:manifest_invalid')
    unsigned = {key: value[key] for key in ('schemaVersion','releaseId','image','sourceCommit','sbomDigest','provenanceDigest')}
    expected = hmac.new(signing_key, _canonical(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, str(value['signature'])):
        raise ReleaseDenied('release:signature_invalid')
    rebuilt = signed_release(
        release_id=unsigned['releaseId'],
        image=unsigned['image'],
        source_commit=unsigned['sourceCommit'],
        sbom_digest=unsigned['sbomDigest'],
        provenance_digest=unsigned['provenanceDigest'],
        signing_key=signing_key,
    )
    if rebuilt != value:
        raise ReleaseDenied('release:manifest_invalid')
    return json.loads(json.dumps(value))


class ReleaseController:
    def __init__(self, state_path: Path, *, signing_key: bytes):
        self.path = state_path
        self.signing_key = signing_key

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {'schemaVersion':1,'current':None,'previous':None,'history':[]}
        if self.path.is_symlink() or not self.path.is_file():
            raise ReleaseDenied('release:state_unsafe')
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReleaseDenied('release:state_invalid') from exc
        if not isinstance(value, dict) or value.get('schemaVersion') != 1 or not isinstance(value.get('history'), list):
            raise ReleaseDenied('release:state_invalid')
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=f'.{self.path.name}.', dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, sort_keys=True, separators=(',', ':'))
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path); os.chmod(self.path, 0o600)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def update(self, release: dict[str, Any], *, health_gate: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        admitted = verify_release(release, signing_key=self.signing_key)
        state = self._load()
        if state['current'] and state['current']['releaseId'] == admitted['releaseId']:
            if state['current'] != admitted:
                raise ReleaseDenied('release:id_conflict')
            return {'status':'idempotent','current':admitted['releaseId'],'trafficChanged':False}
        prior = state['current']
        state['previous'], state['current'] = prior, admitted
        if not health_gate(admitted):
            state['current'], state['previous'] = prior, None
            state['history'].append({'releaseId':admitted['releaseId'],'status':'rolled_back','trafficChanged':False})
            self._write(state)
            return {'status':'rolled_back','current':prior['releaseId'] if prior else None,'trafficChanged':False}
        state['history'].append({'releaseId':admitted['releaseId'],'status':'healthy','trafficChanged':True})
        self._write(state)
        return {'status':'healthy','current':admitted['releaseId'],'trafficChanged':True}

    def rollback(self, *, expected_current: str) -> dict[str, Any]:
        state = self._load()
        if not state['current'] or state['current']['releaseId'] != expected_current:
            raise ReleaseDenied('release:rollback_target_mismatch')
        prior = state['previous']
        if prior is None:
            raise ReleaseDenied('release:rollback_unavailable')
        removed = state['current']; state['current'], state['previous'] = prior, removed
        state['history'].append({'releaseId':removed['releaseId'],'status':'rolled_back','trafficChanged':True})
        self._write(state)
        return {'status':'rolled_back','current':prior['releaseId'],'trafficChanged':True}

    def observe(self) -> dict[str, Any]:
        state = self._load()
        return {'current':state['current']['releaseId'] if state['current'] else None,'previous':state['previous']['releaseId'] if state['previous'] else None,'historyCount':len(state['history'])}
