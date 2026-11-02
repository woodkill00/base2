"""Standard HC producers remain bounded, independently identified and failure-preserving."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.python import shell_png_evidence as collector

HC = 'chromium-high-contrast'
DETAIL = 'media-release-media-detail-fa505-age-and-consequence-context-' + HC
PICKER = 'media-release-media-picker-72bf8-ontained-in-a-real-workflow-' + HC
LIBRARY = 'media-release-media-librar-1b4ce-nsive-and-visually-reviewed-' + HC
OPS = 'operations-release-operati-5407b-ponsive-and-visually-stable-' + HC
PNG = b'\x89PNG\r\n\x1a\n' + b'synthetic transport fixture; not native pixels'


def setup(tmp_path):
    sources = {suite: tmp_path / suite for suite in collector.SUITES}
    for source in sources.values():
        source.mkdir()
    provenance = dict(sourceCommit='a'*40, sourceTree='b'*40, requestedHead='c'*40,
                      runId='123', attempt='1', outcomes={s:'skipped' for s in sources})
    return sources, tmp_path / 'output', provenance


def put(source, case, name, raw=PNG):
    path = source / case / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def test_forced_exact_producer_and_project_rules():
    for suite, case, name in [('media_hc', DETAIL, f'media-detail-{HC}-actual.png'),
                              ('media_hc', PICKER, 'current-media-picker-bottom.png'),
                              ('media_hc', LIBRARY, f'media-library-{HC}-diff.png'),
                              ('operations_hc', OPS, f'operations-center-{HC}-expected.png')]:
        assert collector.allowed(suite, Path(case)/name)
        assert not collector.allowed(suite, Path(case.replace(HC,'chromium-light'))/name)
        assert not collector.allowed(suite, Path('unrelated')/name)
        assert not collector.allowed(suite, Path(case)/'private.png')
    assert not collector.allowed('media_hc', Path(DETAIL)/'current-media-picker.png')
    assert not collector.allowed('operations_hc', Path(OPS)/'current-operations-center-error.png')


def test_forced_fatal_missing_producers_preserves_valid_original_roles(tmp_path):
    sources, output, provenance = setup(tmp_path)
    provenance['outcomes']['media_hc'] = 'failure'
    for role in ['actual', 'expected', 'diff']:
        put(sources['media_hc'], DETAIL, f'media-detail-{HC}-{role}.png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    metadata = json.loads((output/'00/provenance.json').read_bytes())
    assert metadata['packagingComplete'] is False
    assert metadata['outcomes']['media_hc'] == 'failure'
    assert len(metadata['captures']) == 3
    assert {r['role'] for r in metadata['captures']} == {'comparison-actual','comparison-expected','comparison-diff'}
    for row in metadata['captures']:
        assert row['sourceRoot'] == 'media_hc'
        assert row['sha256'] == hashlib.sha256(PNG).hexdigest()
        assert (output/'00'/row['path']).read_bytes() == PNG


def test_forced_mixed_valid_invalid_quarantines_whole_producer(tmp_path):
    sources, output, provenance = setup(tmp_path)
    provenance['outcomes']['media_hc'] = 'failure'
    put(sources['media_hc'], DETAIL, 'current-media-detail.png')
    put(sources['media_hc'], PICKER, 'current-media-picker.png')
    put(sources['media_hc'], PICKER, 'sequence-media-picker.json', b'null')
    put(sources['media_hc'], LIBRARY, 'current-media-library.png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    metadata = json.loads((output/'00/provenance.json').read_bytes())
    assert len(metadata['captures']) == 2
    assert all(PICKER not in r['path'] for r in metadata['captures'])
    assert not list(output.rglob('sequence-media-picker.json'))


def test_forced_workflow_roots_outcomes_and_originals_preserved():
    workflow = Path('.github/workflows/ci-frontend.yml').read_text()
    assert 'SHELL_MEDIA_HC_OUTCOME: ${{ steps.media_hc_acceptance.outcome }}' in workflow
    assert 'SHELL_OPERATIONS_HC_OUTCOME: ${{ steps.operations_hc_acceptance.outcome }}' in workflow
    assert 'name: forced-color-diagnostics' in workflow
    assert "steps.shell_png.outputs.upload_ready == 'true'" in workflow


def test_forced_future_registered_states_and_wrong_producer_excluded():
    for suite, producers in collector.FORCED_PRODUCERS.items():
        for case, (_, states, _, _) in producers.items():
            for state in states:
                assert collector.registered_sequence(suite, case, state)
                for role in ['actual', 'expected', 'diff']:
                    assert collector.allowed(suite, Path(case)/f'sequence-{state}-000-{role}.png')
                assert collector.allowed(suite, Path(case)/f'current-continuous-{state}-focus.png')
            assert not collector.registered_sequence(suite, case, 'private-state')
    assert not collector.registered_sequence('media_hc', DETAIL, 'media-picker')
    assert not collector.allowed('operations_hc', Path(OPS)/'sequence-operations-center-error-000-actual.png')


def test_forced_declared_missing_root_fails_but_skipped_root_is_explicit(tmp_path):
    sources, output, provenance = setup(tmp_path)
    sources['operations_hc'].rmdir()
    provenance['outcomes']['operations_hc'] = 'success'
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    d = json.loads((output/'00/provenance.json').read_bytes())
    assert {'scope':'operations_hc-missing-producer','rejectedProducerCount':1} in d['packagingErrors']
    assert d['suites']['operations_hc']['sourcePresent'] is False


def test_forced_bounded_partition_hashes_and_zip_wrapper(tmp_path, monkeypatch):
    import io
    import zipfile
    sources, output, provenance = setup(tmp_path)
    monkeypatch.setattr(collector, 'BUDGET', len(PNG)*2)
    for role in ['actual','expected','diff']:
        put(sources['media_hc'], DETAIL, f'media-detail-{HC}-{role}.png')
    collector.stage(sources, output, provenance)
    shards = sorted(output.iterdir())
    assert len(shards) == 2
    rows = []
    for shard in shards:
        d = json.loads((shard/'provenance.json').read_bytes())
        rows.extend(d['captures'])
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as z:
            for p in shard.rglob('*'):
                if p.is_file():
                    z.write(p, p.relative_to(shard))
        assert len(stream.getvalue()) < 32*1024*1024
    assert len(rows) == 3
    assert len({r['path'] for r in rows}) == 3
    assert {r['sha256'] for r in rows} == {hashlib.sha256(PNG).hexdigest()}


def test_forced_unknown_json_and_null_observation_quarantine(tmp_path):
    sources, output, provenance = setup(tmp_path)
    put(sources['media_hc'], LIBRARY, 'current-media-library.png')
    put(sources['media_hc'], LIBRARY, 'media-viewport-observations.json', b'null')
    put(sources['media_hc'], DETAIL, 'private.json', b'{"private":"excluded"}')
    put(sources['media_hc'], DETAIL, 'current-media-detail.png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    d = json.loads((output/'00/provenance.json').read_bytes())
    assert len(d['captures']) == 1 and DETAIL in d['captures'][0]['path']
    assert not d['diagnostics']
    assert 'private' not in json.dumps(d)


def test_forced_directory_names_are_bound_to_pinned_fixture_titles():
    import re
    for suite, producers in collector.FORCED_PRODUCERS.items():
        file = 'media-release' if suite == 'media_hc' else 'operations-release'
        folder = 'media' if suite == 'media_hc' else 'operations'
        source = Path(f'react-app/e2e/{folder}/{file}.spec.ts').read_text()
        for case, (title, _, _, _) in producers.items():
            assert f"test('{title}'" in source
            value = file + '-' + re.sub(r'[\x00-\x2c\x2e-\x2f\x3a-\x40\x5b-\x60\x7b-\x7f]+', '-', title)
            if len(value) > 60:
                value = value[:26] + '-' + hashlib.sha1(value.encode()).hexdigest()[:5] + '-' + value[-27:]
            assert case == value + '-' + HC


def test_forced_registered_sequence_crossbinds_continuous_bytes(tmp_path):
    # Reuse the existing decoded synthetic comparison fixture, never native pixels.
    import shutil

    from scripts.tests.test_continuous_evidence import receipt as make_receipt
    from scripts.tests.test_sequence_evidence import comparison as make_comparison
    initial = make_receipt.__wrapped__(tmp_path)
    path, data = make_comparison.__wrapped__(initial)
    (tmp_path / 'roots').mkdir()
    sources, output, provenance = setup(tmp_path / 'roots')
    provenance.update(runId='1')
    case = sources['media_hc'] / PICKER
    case.mkdir()
    native_path = path.with_name('continuous-media.json')
    native = json.loads(native_path.read_bytes())
    for original in tmp_path.glob('*.png'):
        shutil.copyfile(original, case / original.name.replace('media-', 'media-picker-'))
    def adapt(value):
        encoded = json.dumps(value).replace('media-', 'media-picker-').replace('"media"', '"media-picker"')
        return json.loads(encoded)
    native, data = adapt(native), adapt(data)
    # The state substitution above must not rename the authored spec directory.
    data['referenceManifest'] = 'e2e/media/media-release.spec.ts-snapshots/sequence-media-picker.json'
    for bound in (native, data['binding']):
        bound.update(project=HC, test=collector.FORCED_PRODUCERS['media_hc'][PICKER][0])
    (case/'continuous-media-picker.json').write_text(json.dumps(native))
    (case/'sequence-media-picker.json').write_text(json.dumps(data))
    collector.stage(sources, output, provenance)
    saved = json.loads((output/'00/provenance.json').read_bytes())
    assert saved['packagingComplete']
    assert len(saved['diagnostics']) == 2
    assert len(saved['captures']) == 8
    assert sum(r['role'] == 'comparison-actual' for r in saved['captures']) == 4
    for row in saved['captures'] + saved['diagnostics']:
        raw = (output/'00'/row['path']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']


def test_maximum_payload_metadata_and_member_names_fit_wrapper_limit():
    import io
    import zipfile
    stream = io.BytesIO()
    count = 2048
    payload = b'x' * (collector.BUDGET // count)
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as z:
        for index in range(count):
            name = f'{index:04}/' + 'x' * (collector.MAX_PATH_BYTES - 9) + '.png'
            assert len(name.encode()) == collector.MAX_PATH_BYTES
            z.writestr(name, payload)
        z.writestr('provenance.json', b' ' * collector.MAX_METADATA)
    assert len(stream.getvalue()) < 32 * 1024 * 1024


@pytest.mark.parametrize('missing', [None, 0, 2, 4, 'all'])
def test_forced_observation_requires_every_corresponding_validated_viewport(tmp_path, missing):
    from scripts.tests.test_visual_matrix_artifacts import media_observation_fixture
    (tmp_path / 'observation-fixture').mkdir()
    _, _, _, _, observation = media_observation_fixture(tmp_path / 'observation-fixture')
    observation['project'] = HC
    roots = tmp_path / 'roots'
    roots.mkdir()
    sources, output, provenance = setup(roots)
    provenance['outcomes']['media_hc'] = 'failure'
    put(sources['media_hc'], DETAIL, 'current-media-detail.png')
    put(sources['media_hc'], PICKER, 'current-media-picker.png')
    put(sources['media_hc'], LIBRARY, 'current-media-library.png')
    raw = json.dumps(observation).encode()
    put(sources['media_hc'], LIBRARY, 'media-viewport-observations.json', raw)
    for index in (0, 2, 4):
        if missing not in (index, 'all'):
            put(sources['media_hc'], LIBRARY, f'current-media-library-viewport-{index}.png')
    if missing is None:
        collector.stage(sources, output, provenance)
    else:
        with pytest.raises(collector.PackagingIncomplete):
            collector.stage(sources, output, provenance)
    result = json.loads((output/'00/provenance.json').read_bytes())
    assert result['packagingComplete'] is (missing is None)
    assert result['outcomes']['media_hc'] == 'failure'
    if missing is None:
        assert len(result['captures']) == 6
        assert result['diagnostics'][0]['sha256'] == hashlib.sha256(raw).hexdigest()
    else:
        assert len(result['captures']) == 2
        assert all(LIBRARY not in row['path'] for row in result['captures'])
        assert not result['diagnostics']
    for row in result['captures'] + result['diagnostics']:
        retained = (output/'00'/row['path']).read_bytes()
        assert hashlib.sha256(retained).hexdigest() == row['sha256']
        assert len(retained) == row['bytes']


def test_hc_excludes_desktop_only_legacy_cancellation_outputs():
    for name in ['current-operations-center-cancel-confirmation.png',
                 'operations-center-cancel-confirmation-actual.png',
                 'operations-center-cancel-confirmation-expected.png',
                 'operations-center-cancel-confirmation-diff.png',
                 'sequence-operations-center-cancel-confirmation-000-actual.png',
                 'current-continuous-operations-center-cancel-confirmation-000.png']:
        assert not collector.allowed('operations_hc', Path(OPS)/name)
    assert not collector.registered_sequence('operations_hc', OPS, 'operations-center-cancel-confirmation')
    assert collector.registered_sequence('operations_hc', OPS, 'operations-cancel')
    assert collector.registered_sequence('operations_hc', OPS, 'operations-center-' + HC)
