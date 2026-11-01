"""Bounded synthetic shell PNG copies; original results and artifacts stay authoritative."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from scripts.python import continuous_evidence, sequence_evidence

BUDGET = 28 * 1024 * 1024
SLOTS = 480
MAX_FILES = 65536
MAX_METADATA = 512 * 1024
TOTAL_BYTES = 6 * 1024 * 1024 * 1024
MAX_PATH_BYTES = 300
SUITES = ('layout', 'volcano', 'settings', 'workspace', 'journeys')
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
    sample = re.fullmatch(r'current-scrollport-([a-z0-9-]{1,90})-(?:top|middle|footer)\.png', relative.name)
    if sample:
        return sequence_evidence.registered(suite, case, sample[1])
    comparison = sequence_evidence.IMAGE.fullmatch(relative.name)
    if comparison:
        return sequence_evidence.registered(suite,case,comparison[1])
    if suite in ('layout', 'volcano'):
        return any(case.startswith(prefix + '-') for prefix in LAYOUT_CASES) and bool(LAYOUT_NAMES.fullmatch(relative.name))
    if suite == 'journeys':
        return case.startswith('public-journeys-public-jou-') and bool(re.fullmatch(
            rf'(?:{COMMON}|contact-received|search-paginated|(?:contact-received-390|search-paginated-1440)-(?:actual|expected|diff))\.png',relative.name))
    prefix = 'settings-release-' if suite == 'settings' else 'workspace-release-'
    names = SETTINGS_NAMES if suite == 'settings' else WORKSPACE_NAMES
    return case.startswith(prefix) and bool(names.fullmatch(relative.name))


def image_role(name: str) -> str:
    if sequence_evidence.NAME.fullmatch(name):
        return 'sequence-comparison-receipt'
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


class PackagingIncomplete(ValueError):
    """Validated parts exist, but incomplete packaging remains a fatal CI failure."""


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
    rejected = set()
    errors: dict[str, int] = {}
    bound_frames = set()
    bound_comparisons = set()
    states = {}
    # No generic JSON, report HTML, traces, video, fixtures or source trees are copied.
    for suite, source in sources.items():
        safe(source)
        states[suite] = {'sourcePresent': source.is_dir(), 'captures': 0, 'excludedPngCount': 0,
                         'nativeOutcome': provenance['outcomes'][suite], 'producerExclusions': [], 'unknownExcludedCount': 0}
        if not source.exists():
            continue
        if not source.is_dir():
            raise ValueError('source must be a directory')
        for path in sorted(source.rglob('*')):
            relative = path.relative_to(source)
            producer = (suite, relative.parts[0])
            if producer in rejected:
                continue
            try:
                safe(path)
                comparison_receipt = sequence_evidence.NAME.fullmatch(path.name)
                if comparison_receipt:
                    rel = path.relative_to(source)
                    if len(rel.parts) != 2 or not sequence_evidence.registered(suite,rel.parts[0],comparison_receipt[1]):
                        continue
                    if not path.is_file() or path.stat().st_size > sequence_evidence.BUDGET:
                        raise ValueError('oversized sequence receipt')
                    raw = path.read_bytes()
                    data = sequence_evidence.validate(raw,path,provenance['sourceCommit'],provenance['sourceTree'],run=str(provenance['runId']),attempt=str(provenance['attempt']))
                    for row in sequence_evidence.images(data):
                        target = path.parent/row['file']
                        if target in bound_comparisons:
                            raise ValueError('duplicate sequence image binding')
                        bound_comparisons.add(target)
                    members.append((path,f'{suite}/{rel.as_posix()}',len(raw),hashlib.sha256(raw).hexdigest()))
                    continue
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
                        rel = path.relative_to(source)
                        # Only known producer-generated attachment copies may disclose names.
                        if (len(rel.parts)==3 and rel.parts[1]=='attachments'
                            and re.fullmatch(r'(?:Rendered-page|page|viewport|zoom|settings-release-before-axe|settings-release-restored-after-controls|settings-negative-controls-before-axe)-[a-f0-9]{40}\.png',rel.name)
                            and allowed(suite,Path(rel.parts[0])/('page.png' if suite in ('layout','volcano') else 'settings-release-before-axe.png'))):
                            if len(states[suite]['producerExclusions']) >= 1024:
                                raise ValueError('producer exclusion inventory bound')
                            states[suite]['producerExclusions'].append({'path':rel.as_posix(),'classification':'known-attachment-copy-excluded'})
                        else:
                            states[suite]['unknownExcludedCount'] += 1
                    continue
                if not path.is_file() or path.stat().st_size > BUDGET:
                    raise ValueError('non-regular or oversized PNG')
                raw = path.read_bytes()
                if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError('invalid PNG signature')
                members.append((path, f'{suite}/{path.relative_to(source).as_posix()}',
                                len(raw), hashlib.sha256(raw).hexdigest()))
                states[suite]['captures'] += 1
            except (ValueError, OSError):
                rejected.add(producer)
                errors[suite] = errors.get(suite, 0) + 1
                members = [item for item in members if tuple(Path(item[1]).parts[:2]) != producer]
                bound_frames = {p for p in bound_frames if p.parent != source / relative.parts[0]}
                bound_comparisons = {p for p in bound_comparisons if p.parent != source / relative.parts[0]}
    # Every continuous frame must have a validated original receipt in the same
    # producer directory. Unknown PNGs remain excluded and counted separately.
    unbound = {tuple(Path(item[1]).parts[:2]) for item in members
               if (continuous_evidence.FRAME.fullmatch(item[0].name) and item[0] not in bound_frames)
               or (sequence_evidence.IMAGE.fullmatch(item[0].name) and item[0] not in bound_comparisons)}
    for unbound_producer in unbound:
        errors[unbound_producer[0]] = errors.get(unbound_producer[0], 0) + 1
        members = [item for item in members if tuple(Path(item[1]).parts[:2]) != unbound_producer]
    # Budget rejection is producer-atomic: never retain a receipt after dropping
    # some of its frames. Names/content of rejected producers are not disclosed.
    def reject_last_producer():
        key = tuple(Path(members[-1][1]).parts[:2])
        members[:] = [item for item in members if tuple(Path(item[1]).parts[:2]) != key]
        errors['budget'] = errors.get('budget', 0) + 1

    while members and (len(members) > MAX_FILES or sum(item[2] for item in members) > TOTAL_BYTES
                       or any(len(item[1].encode()) > MAX_PATH_BYTES for item in members)):
        reject_last_producer()
    def metadata_bytes(bucket, index, shards):
        metadata = {**provenance, 'schemaVersion': 2, 'packagingComplete': not errors,
                    'packagingErrors': [{'scope': key, 'rejectedProducerCount': count} for key, count in sorted(errors.items())], 'shard': index, 'shards': shards,
                    'suites': states, 'captureCount': sum(p.suffix == '.png' for p, *_ in members),
                    'diagnosticReceiptCount': sum(p.suffix == '.json' for p, *_ in members),
                    'scope': 'Synthetic diagnostic PNG copies; not approved references or visual acceptance. PNG bytes hashed, not decoded by packager.',
                    'captures': [{'path': name, 'bytes': count, 'sha256': digest,
                                  'sourceRoot': name.split('/')[0],
                                  'role': image_role(Path(name).name)}
                                 for _, name, count, digest in bucket if Path(name).suffix == '.png'],
                    'diagnostics': [{'path': name, 'bytes': count, 'sha256': digest,
                                     'sourceRoot': name.split('/')[0], 'role': image_role(Path(name).name)}
                                    for _, name, count, digest in bucket if Path(name).suffix == '.json']}
        encoded = (json.dumps(metadata, indent=2) + '\n').encode()
        return encoded

    # Repeated safe exclusion names are optional detail, never capture identities.
    # If their base receipt is too large, retain exact counts and make omission fatal.
    if (len(metadata_bytes([], SLOTS, SLOTS)) > MAX_METADATA
            or any(len(metadata_bytes([item], SLOTS, SLOTS)) > MAX_METADATA for item in members)):
        for state in states.values():
            names = state['producerExclusions']
            if names:
                state['omittedProducerExclusionCount'] = len(names)
                state['producerExclusions'] = []
        errors['exclusion-metadata-budget'] = 1
    if len(metadata_bytes([], SLOTS, SLOTS)) > MAX_METADATA:
        raise ValueError('base metadata exceeds bound')
    while True:
        for suite in states:
            states[suite]['captures'] = sum(Path(name).suffix == '.png' and name.split('/')[0] == suite
                                            for _, name, *_ in members)
        buckets: list[list] = [[]]
        size = 0
        impossible = False
        for item in members:
            if len(metadata_bytes([item], SLOTS, SLOTS)) > MAX_METADATA:
                impossible = True
                break
            if buckets[-1] and (size + item[2] > BUDGET or len(buckets[-1]) >= 2048
                                or len(metadata_bytes(buckets[-1] + [item], SLOTS, SLOTS)) > MAX_METADATA):
                buckets.append([])
                size = 0
            buckets[-1].append(item)
            size += item[2]
        if not impossible and len(buckets) <= SLOTS:
            break
        reject_last_producer()
    for index, bucket in enumerate(buckets):
        encoded = metadata_bytes(bucket, index, len(buckets))
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
    if errors:
        raise PackagingIncomplete('incomplete bounded packaging; validated parts retained')


def upload_action(output: Path, destination: Path) -> None:
    """Only pinned, data-only upload steps for verified bounded shard directories."""
    safe(output)
    safe(destination)
    if output != Path('.artifacts/shell-png') or destination != Path('.artifacts/shell-upload-action') or destination.exists():
        raise ValueError('unexpected upload action path')
    shards = list(output.iterdir())
    if any(not re.fullmatch(r'[0-9]{2,3}', p.name) for p in shards):
        raise ValueError('unexpected shard name')
    shards.sort(key=lambda p: int(p.name))
    if not 1 <= len(shards) <= SLOTS:
        raise ValueError('shell artifact count bound')
    steps = []
    for index, shard in enumerate(shards):
        safe(shard)
        if shard.name != f'{index:02}' or not shard.is_dir():
            raise ValueError('unexpected shell shard')
        metadata = shard / 'provenance.json'
        safe(metadata)
        if not metadata.is_file() or metadata.stat().st_size > MAX_METADATA:
            raise ValueError('missing shard provenance')
        data = json.loads(metadata.read_bytes())
        rows = data['captures'] + data['diagnostics']
        if len(rows) > 2048 or sum(r['bytes'] for r in rows) > BUDGET:
            raise ValueError('shell shard payload bound')
        expected = {'provenance.json', *(r['path'] for r in rows)}
        actual = set()
        for path in shard.rglob('*'):
            safe(path)
            if path.is_file():
                actual.add(path.relative_to(shard).as_posix())
        if actual != expected:
            raise ValueError('unexpected shell upload content')
        for row in rows:
            path = shard / row['path']
            if path.stat().st_size != row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('shell upload identity mismatch')
        steps.append({'name': f'Retain shell shard {index:02}', 'if': 'always()',
                      'uses': 'actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f',
                      'with': {'name': f'shell-png-{index:02}-' + '${{ github.run_id }}-${{ github.run_attempt }}',
                               'path': f'.artifacts/shell-png/{index:02}/', 'compression-level': 0,
                               'if-no-files-found': 'error', 'retention-days': 7}})
    destination.mkdir(parents=True)
    (destination/'action.yml').write_text(json.dumps({'name':'Bounded shell evidence','description':'Exact synthetic capture shards',
        'runs':{'using':'composite','steps':steps}},indent=2)+'\n')


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
               'workspace': Path('.artifacts/workspace-124'),
               'journeys': Path(f'.artifacts/journeys-ci-{run}-{attempt}-journeys')}
    failure = None
    try:
        stage(sources, Path('.artifacts/shell-png'), {
            'sourceCommit': git('HEAD'), 'sourceTree': git('HEAD^{tree}'),
            'requestedHead': os.environ['SHELL_REQUESTED_HEAD'], 'runId': run, 'attempt': attempt,
            'outcomes': {suite: os.environ[f'SHELL_{suite.upper()}_OUTCOME'] for suite in SUITES},
        })
    except PackagingIncomplete as error:
        failure = error
    upload_action(Path('.artifacts/shell-png'), Path('.artifacts/shell-upload-action'))
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
        stream.write('upload_ready=true\n')
    if failure:
        raise failure



if __name__ == '__main__':
    main()
