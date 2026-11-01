"""Adversarial transport validation of synthetic continuous viewport receipts."""
import copy
import hashlib
import json

import pytest

from scripts.python.continuous_evidence import validate


@pytest.fixture
def receipt(tmp_path):
    data = dict(schemaVersion=1, fixtureScope='synthetic-project-tests',
                scope='Diagnostic continuous viewports; not visual acceptance.',
                sourceCommit='a' * 40, sourceTree='b' * 40, runId='1', attempt='1',
                project='chromium-compact', test='synthetic unit case', route='/media',
                state='media', target='content-scrollport', extent=1000,
                segmentLimit=64, reachedEnd=True, complete=True, errors=[], segments=[])
    for i, (start, end) in enumerate([(0, 400), (300, 700), (600, 1000)]):
        name = f'current-continuous-media-{i:03d}.png'
        raw = b'\x89PNG\r\n\x1a\nsynthetic-unit-bytes'
        (tmp_path / name).write_bytes(raw)
        data['segments'].append(dict(index=i, route='/media', start=start, end=end, extent=1000,
                                     offset=start, file=name, sha256=hashlib.sha256(raw).hexdigest(),
                                     bytes=len(raw), height=400, inset=0, scale=1, max=600,
                                     viewport=[320, 568, 1], rect=[0, 0, 320, 400]))
    return tmp_path / 'continuous-media.json', data


def check(receipt):
    path, data = receipt
    return validate(json.dumps(data).encode(), path, 'a' * 40, 'b' * 40, 'chromium-compact')


def test_complete_and_incomplete_are_separate(receipt):
    assert check(receipt)['complete']
    receipt[1].update(complete=False, reachedEnd=False, errors=['incomplete'])
    receipt[1]['segments'].pop()
    assert not check(receipt)['complete']


@pytest.mark.parametrize('mutation', [
    lambda d: d['segments'][1].update(start=450),
    lambda d: d['segments'][1].update(index=0),
    lambda d: d['segments'][1].update(offset=0),
    lambda d: d['segments'][1].update(route='/other'),
    lambda d: d['segments'][1].update(extent=1200),
    lambda d: d['segments'][1].update(file='../private.png'),
    lambda d: d['segments'][1].update(sha256='c' * 64),
    lambda d: d['segments'][1].update(private='secret'),
    lambda d: d.update(sourceCommit='c' * 40),
    lambda d: d.update(segments=d['segments'] * 22),
    lambda d: d.update(route='/media?token=private'),
    lambda d: d.update(errors=['incomplete']),
    lambda d: d.update(reachedEnd=False),
    lambda d: d['segments'][-1].update(max=1200),
])
def test_reject_tamper_gaps_route_changes_limits_and_private_fields(receipt, mutation):
    data = copy.deepcopy(receipt[1])
    mutation(data)
    with pytest.raises(ValueError):
        check((receipt[0], data))


def test_reject_duplicate_json_keys(receipt):
    path, data = receipt
    raw = json.dumps(data).replace('"schemaVersion": 1', '"schemaVersion": 1, "schemaVersion": 1')
    with pytest.raises(ValueError):
        validate(raw.encode(), path, 'a' * 40, 'b' * 40)


def test_reject_symlink_image(receipt, tmp_path):
    image = tmp_path / receipt[1]['segments'][0]['file']
    moved = tmp_path / 'other.png'
    image.rename(moved)
    image.symlink_to(moved)
    with pytest.raises(ValueError):
        check(receipt)


def test_failed_collapsed_offscreen_observation_is_retained_without_acceptance(receipt):
    receipt[1].update(complete=False, reachedEnd=False, errors=['geometry'])
    receipt[1]['segments'][0].update(start=-40, end=-10, height=0)
    assert not check(receipt)['complete']
    receipt[1].update(complete=True, reachedEnd=True, errors=[])
    with pytest.raises(ValueError):
        check(receipt)


def test_run_and_attempt_must_match_enclosing_provenance(receipt):
    path, data = receipt
    for run, attempt in [('2', '1'), ('1', '2')]:
        with pytest.raises(ValueError):
            validate(json.dumps(data).encode(), path, 'a' * 40, 'b' * 40, run=run, attempt=attempt)


@pytest.mark.parametrize('extra', [False, True])
def test_shell_roundtrip_binds_exact_frames_and_original_receipt(receipt, tmp_path, extra):
    from scripts.python import shell_png_evidence as shell
    path, data = receipt
    sources = {suite: tmp_path / suite for suite in shell.SUITES}
    for source in sources.values():
        source.mkdir()
    case = sources['volcano'] / 'volcano-preservation-unit-chromium'
    case.mkdir()
    for row in data['segments']:
        (path.parent / row['file']).rename(case / row['file'])
    original = json.dumps(data).encode()
    (case / path.name).write_bytes(original)
    if extra:
        (case / 'current-continuous-media-003.png').write_bytes((case / data['segments'][0]['file']).read_bytes())
    provenance = dict(sourceCommit='a' * 40, sourceTree='b' * 40, requestedHead='c' * 40,
                      runId='1', attempt='1', outcomes={s: 'failure' for s in sources})
    output = tmp_path / 'bounded'
    if extra:
        with pytest.raises(ValueError, match='unbound'):
            shell.stage(sources, output, provenance)
    else:
        shell.stage(sources, output, provenance)
        assert next(output.rglob(path.name)).read_bytes() == original
        assert len(list(output.rglob('current-continuous-*.png'))) == 3
        metadata = [json.loads(p.read_text()) for p in output.rglob('provenance.json')]
        assert all(m['schemaVersion'] == 2 and m['captureCount'] == 3 and m['diagnosticReceiptCount'] == 1 for m in metadata)
        assert sum(len(m['captures']) for m in metadata) == 3
        assert sum(len(m['diagnostics']) for m in metadata) == 1


def test_matrix_roundtrip_keeps_failed_outcome_and_binds_every_frame(receipt, tmp_path):
    import zipfile

    from scripts.python import visual_matrix_artifacts as matrix
    path, data = receipt
    source = tmp_path / 'matrix'
    case = source / 'test-results' / 'operations-unit-chromium-compact'
    case.mkdir(parents=True)
    for row in data['segments']:
        (path.parent / row['file']).rename(case / row['file'])
    (case / path.name).write_text(json.dumps(data))
    before = dict(sourceCommit='a' * 40, sourceTree='b' * 40, runId='1', attempt='1', matrix='operations',
                  expectedTests=[dict(project='chromium-compact', title='synthetic unit case', expectedStatus='passed')])
    (source / 'source-before.json').write_text(json.dumps(before))
    (source / 'source-after.json').write_text('{"nativeOutcome":"failure"}')
    output = tmp_path / 'matrix-output'
    matrix.stage(source, output)
    members = {}
    for archive in output.glob('*.zip'):
        with zipfile.ZipFile(archive) as z:
            members.update({name: z.read(name) for name in z.namelist()})
    assert sum(name.endswith('.png') for name in members) == 3
    assert any(name.endswith(path.name) for name in members)
    assert members['source-after.json'] == b'{"nativeOutcome":"failure"}'


def test_gapless_but_nonoverlapping_frames_cannot_claim_complete_review(receipt):
    receipt[1]['segments'][1].update(start=400, end=800, offset=400)
    with pytest.raises(ValueError):
        check(receipt)


def test_one_pixel_port_cannot_claim_thousand_pixel_coverage(receipt):
    data = receipt[1]
    data['segments'] = data['segments'][:1]
    data['segments'][0].update(start=0, end=1000, extent=1000, height=1,
                               inset=0, scale=1, max=0, offset=0,
                               rect=[0, 0, 320, 1], viewport=[320, 568, 1])
    with pytest.raises(ValueError):
        check(receipt)


@pytest.mark.parametrize('change', [
    {'start': 1.1}, {'end': 401.1}, {'extent': 1002}, {'height': 1000},
    {'scale': 0}, {'scale': -1}, {'scale': 2}, {'inset': -1}, {'inset': 401},
    {'max': -1}, {'offset': -1}, {'rect': [400, 0, 320, 400]},
    {'rect': [0, 600, 320, 400]}, {'rect': [10, 0, 320, 400]}, {'rect': [0, 0, 0, 400]},
])
def test_geometry_must_independently_derive_intervals(receipt, change):
    receipt[1]['segments'][0].update(change)
    with pytest.raises(ValueError):
        check(receipt)


def test_scaled_inset_geometry_can_prove_real_coverage(receipt):
    for row in receipt[1]['segments']:
        row.update(height=420, inset=20, max=600, scale=0.5,
                   rect=[0, 10, 320, 210])
    assert check(receipt)['complete']


def test_complete_offscreen_geometry_rejected_but_failed_observation_retained(receipt):
    row = receipt[1]['segments'][0]
    row.update(rect=[0, 600, 320, 400], start=0, end=-32)
    with pytest.raises(ValueError):
        check(receipt)
    receipt[1].update(complete=False, reachedEnd=False, errors=['geometry'])
    assert not check(receipt)['complete']
