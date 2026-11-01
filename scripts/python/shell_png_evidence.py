"""Bounded synthetic shell PNG copies; original results and artifacts stay authoritative."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from scripts.python import continuous_evidence

BUDGET = 28 * 1024 * 1024
SLOTS = 16
MAX_FILES = 4096
MAX_METADATA = 512 * 1024
SUITES = ('layout', 'volcano', 'settings', 'workspace')
LAYOUT_CASES = ('appearance-preferences', 'interaction-contract', 'representative',
                'route-families', 'settings-interruption', 'workspace-policy-settings',
                'workspace-review', 'volcano-preservation', 'accessible-layout',
                'google-security-policy', 'home-controls', 'negative-controls')
COMMON = r'(?:current-scrollport-(?:top|middle|footer)|current-continuous-[a-z0-9-]{1,90}-(?:[0-9]{3}|focus)|test-failed-[0-9]+)'
LAYOUT_NAMES = re.compile(
    rf'(?:{COMMON}|page|viewport|zoom|empty-auth-errors|light-zoom|'
    r'volcano-(?:390|1440)-(?:home|left|right|palette)-(?:actual|expected|diff)|'
    r'appearance-(?:default|saved)-[0-9]+|settings-leave-(?:en|ar)-forced-colors|'
    r'dock-focus-(?:compact|landscape|desktop|rtl|rtl-large-text|forced|zoom)-base2-(?:left-menu-toggle|right-utility-toggle|scroll-ascend|scroll-descend)|'
    r'movement-(?:compact|landscape|desktop|rtl|rtl-large-text|forced|zoom)-(?:0|0\.5|1))\.png')
SETTINGS_NAMES = re.compile(
    rf'(?:{COMMON}|settings-release-before-axe|settings-negative-controls-before-axe|'
    r'settings-release-restored-after-controls|settings-release-[a-z0-9-]+-(?:actual|expected|diff))\.png')
WORKSPACE_NAMES = re.compile(
    rf'(?:{COMMON}|workspace-(?:records|schema|imports|exports)-(?:post-assert|'
    r'[a-z0-9-]+-(?:actual|expected|diff)))\.png')


def safe(path: Path) -> None:
    if '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('traversal or symlink rejected')


def allowed(suite: str, relative: Path) -> bool:
    if len(relative.parts) != 2 or not re.fullmatch(r'[a-zA-Z0-9_-]+', relative.parts[0]):
        return False
    case = relative.parts[0]
    if suite in ('layout', 'volcano'):
        return any(case.startswith(prefix + '-') for prefix in LAYOUT_CASES) and bool(LAYOUT_NAMES.fullmatch(relative.name))
    prefix = 'settings-release-' if suite == 'settings' else 'workspace-release-'
    names = SETTINGS_NAMES if suite == 'settings' else WORKSPACE_NAMES
    return case.startswith(prefix) and bool(names.fullmatch(relative.name))


def image_role(name: str) -> str:
    if continuous_evidence.NAME.fullmatch(name):
        return 'continuous-diagnostic-receipt'
    if continuous_evidence.FRAME.fullmatch(name) and name.endswith('-focus.png'):
        return 'original-focus-context'
    for role in ('actual', 'expected', 'diff'):
        if name.endswith(f'-{role}.png'):
            return f'comparison-{role}'
    if name.startswith('test-failed-'):
        return 'failure-diagnostic'
    return 'current-diagnostic'


def stage(sources: dict[str, Path], output: Path, provenance: dict) -> None:
    if set(provenance) != {'sourceCommit', 'sourceTree', 'requestedHead', 'runId', 'attempt', 'outcomes'}:
        raise ValueError('unexpected provenance fields')
    safe(output)
    if output.exists():
        raise ValueError('output must be fresh')
    if set(sources) != set(SUITES) or set(provenance['outcomes']) != set(SUITES):
        raise ValueError('exact suite inventory required')
    if any(v not in ('success', 'failure', 'skipped', 'cancelled') for v in provenance['outcomes'].values()):
        raise ValueError('invalid native outcome')
    for field in ('sourceCommit', 'sourceTree', 'requestedHead'):
        if not re.fullmatch('[0-9a-f]{40}', provenance[field]):
            raise ValueError('invalid source identity')
    for field in ('runId', 'attempt'):
        if not re.fullmatch('[0-9]+', provenance[field]):
            raise ValueError('invalid run identity')
    members = []
    bound_frames = set()
    states = {}
    # No generic JSON, report HTML, traces, video, fixtures or source trees are copied.
    for suite, source in sources.items():
        safe(source)
        states[suite] = {'sourcePresent': source.is_dir(), 'captures': 0, 'excludedPngCount': 0,
                         'nativeOutcome': provenance['outcomes'][suite]}
        if not source.exists():
            continue
        if not source.is_dir():
            raise ValueError('source must be a directory')
        for path in sorted(source.rglob('*')):
            safe(path)
            if continuous_evidence.NAME.fullmatch(path.name):
                # Reuse the exact producer directory allowlist, not arbitrary JSON.
                probe = path.relative_to(source).with_name('current-scrollport-top.png')
                if not allowed(suite, probe):
                    continue
                if not path.is_file() or path.stat().st_size > continuous_evidence.BUDGET:
                    raise ValueError('oversized continuous receipt')
                raw = path.read_bytes()
                data = continuous_evidence.validate(raw, path, provenance['sourceCommit'], provenance['sourceTree'], run=str(provenance['runId']), attempt=str(provenance['attempt']))
                for row in continuous_evidence.capture_rows(data):
                    frame = path.parent / row['file']
                    if frame in bound_frames:
                        raise ValueError('duplicate continuous frame binding')
                    bound_frames.add(frame)
                members.append((path, f'{suite}/{path.relative_to(source).as_posix()}', len(raw), hashlib.sha256(raw).hexdigest()))
                continue
            if not allowed(suite, path.relative_to(source)):
                if path.suffix == '.png' and path.is_file():
                    states[suite]['excludedPngCount'] += 1
                continue
            if not path.is_file() or path.stat().st_size > BUDGET:
                raise ValueError('non-regular or oversized PNG')
            raw = path.read_bytes()
            if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('invalid PNG signature')
            members.append((path, f'{suite}/{path.relative_to(source).as_posix()}',
                            len(raw), hashlib.sha256(raw).hexdigest()))
            states[suite]['captures'] += 1
            if len(members) > MAX_FILES:
                raise ValueError('capture inventory exceeds bound')
    # Every continuous frame must have a validated original receipt in the same
    # producer directory. Unknown PNGs remain excluded and counted separately.
    if {item[0] for item in members if continuous_evidence.FRAME.fullmatch(item[0].name)} != bound_frames:
        raise ValueError('unbound continuous frame')
    if len(members) > MAX_FILES:
        raise ValueError('capture and receipt inventory exceeds bound')
    buckets: list[list] = [[] for _ in range(SLOTS)]
    slot = 0
    size = 0
    for item in members:
        if size + item[2] > BUDGET:
            slot += 1
            size = 0
        if slot >= SLOTS:
            raise ValueError('capture volume exceeds fixed shard capacity; nothing truncated')
        buckets[slot].append(item)
        size += item[2]
    # Every shard includes overall completeness, including empty/missing suites.
    # Outcome is recorded verbatim, never converted into visual acceptance.
    for index, bucket in enumerate(buckets):
        metadata = {**provenance, 'schemaVersion': 2, 'shard': index, 'shards': SLOTS,
                    'suites': states, 'captureCount': sum(p.suffix == '.png' for p, *_ in members),
                    'diagnosticReceiptCount': sum(p.suffix == '.json' for p, *_ in members),
                    'scope': 'Synthetic diagnostic PNG copies; not approved references or visual acceptance. PNG bytes hashed, not decoded by packager.',
                    'captures': [{'path': name, 'bytes': count, 'sha256': digest,
                                  'sourceRoot': name.split('/')[0],
                                  'role': image_role(Path(name).name)}
                                 for _, name, count, digest in bucket if Path(name).suffix == '.png'],
                    'diagnostics': [{'path': name, 'bytes': count, 'sha256': digest,
                                     'sourceRoot': name.split('/')[0], 'role': 'continuous-diagnostic-receipt'}
                                    for _, name, count, digest in bucket if Path(name).suffix == '.json']}
        encoded = (json.dumps(metadata, indent=2) + '\n').encode()
        if len(encoded) > MAX_METADATA:
            raise ValueError('metadata exceeds bound')
        target = output / f'{index:02}'
        target.mkdir(parents=True)
        for path, name, _, digest in bucket:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                raise ValueError('source changed during copy')
        (target / 'provenance.json').write_bytes(encoded)


def main() -> None:
    def git(value: str) -> str:
        return subprocess.check_output(['git', 'rev-parse', value], text=True, timeout=10).strip()

    run = os.environ['GITHUB_RUN_ID']
    attempt = os.environ['GITHUB_RUN_ATTEMPT']
    if not re.fullmatch('[0-9]+', run) or not re.fullmatch('[0-9]+', attempt):
        raise ValueError('invalid run identity')
    sources = {'layout': Path(f'.artifacts/layout-109/ci-{run}-{attempt}-layout'),
               'volcano': Path(f'.artifacts/layout-109/ci-{run}-{attempt}-volcano'),
               'settings': Path('.artifacts/settings-121/release'),
               'workspace': Path('.artifacts/workspace-124')}
    stage(sources, Path('.artifacts/shell-png'), {
        'sourceCommit': git('HEAD'), 'sourceTree': git('HEAD^{tree}'),
        'requestedHead': os.environ['SHELL_REQUESTED_HEAD'], 'runId': run, 'attempt': attempt,
        'outcomes': {suite: os.environ[f'SHELL_{suite.upper()}_OUTCOME'] for suite in SUITES},
    })


if __name__ == '__main__':
    main()
