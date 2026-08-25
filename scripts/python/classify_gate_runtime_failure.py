#!/usr/bin/env python3
"""Classify the latest complete-gate failure without masking product failures."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NATIVE_CORRUPTION = re.compile(
    r'(Fatal Python error:\s*Segmentation fault|\bexit[ _]-11\b|'
    r'worker process exited unexpectedly \(code=null, signal=SIGSEGV\)|'
    r'malloc_consolidate\(\)|unaligned fastbin|corrupted double-linked list|'
    r'double free or corruption)',
    re.IGNORECASE,
)


def classify(result_path: Path) -> dict:
    try:
        result = json.loads(result_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('classification:result_invalid') from exc
    if result.get('overallStatus') != 'failed' or not isinstance(result.get('checks'), list):
        return {'nativeCorruption': False, 'reason': 'gate_not_failed'}
    failed = [item for item in result['checks'] if item.get('status') == 'failed']
    if not failed:
        return {'nativeCorruption': False, 'reason': 'no_failed_checks'}
    evidence_root = result_path.parent
    native = []
    non_native = []
    for item in failed:
        artifact = item.get('artifact')
        if not isinstance(artifact, str):
            non_native.append(item.get('id'))
            continue
        try:
            text = (evidence_root / artifact).read_text(encoding='utf-8', errors='replace')
        except OSError:
            non_native.append(item.get('id'))
            continue
        (native if NATIVE_CORRUPTION.search(text) else non_native).append(item.get('id'))
    return {
        'nativeCorruption': bool(native) and not non_native,
        'sourceCommit': result.get('sourceCommit'),
        'nativeFailedChecks': native,
        'nonNativeFailedChecks': non_native,
        'evidence': str(result_path),
    }


def latest(root: Path) -> Path:
    paths = sorted(root.glob('*/result.json'), key=lambda path: path.parent.name)
    if not paths:
        raise ValueError('classification:no_gate_evidence')
    return paths[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path)
    parser.add_argument('--evidence-root', type=Path, default=Path('.artifacts/complete-gate'))
    args = parser.parse_args()
    value = classify(args.result or latest(args.evidence_root))
    print(json.dumps(value, sort_keys=True))
    return 75 if value['nativeCorruption'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
