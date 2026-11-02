"""Bounded shell collection never mutates test inputs or native outcomes."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.python import shell_png_evidence as collector

PNG = b'\x89PNG\r\n\x1a\n' + b'unit fixture, not native evidence'


def test_selected_workspace_edit_states_are_narrowly_registered_and_preserve_exact_bytes(tmp_path):
    sources, output, provenance = setup(tmp_path)
    names = ['workspace-records-selected-edit-post-assert.png',
             'workspace-records-selected-saved-post-assert.png',
             'current-scrollport-workspace-records-selected-edit-footer.png']
    for name in names:
        put(sources['workspace'], 'workspace-release-selected-9c572-aves-or-discards-explicitly-chromium-compact/' + name)
    for name in ['workspace-records-selected-private.png', 'private-record.json']:
        put(sources['workspace'], 'workspace-release-selected-9c572-aves-or-discards-explicitly-chromium-compact/' + name)
    collector.stage(sources, output, provenance)
    data = json.loads((output / '00/provenance.json').read_text())
    assert data['captureCount'] == 3
    for row in data['captures']:
        assert row['role'] == 'current-diagnostic'
        assert row['sourceRoot'] == 'workspace'
        assert row['sha256'] == hashlib.sha256(PNG).hexdigest()
        assert (output / '00' / row['path']).read_bytes() == PNG
    assert not collector.allowed('workspace', Path('unrelated-case/workspace-records-selected-edit-post-assert.png'))
    assert not collector.allowed('workspace', Path('workspace-release-unit/current-scrollport-workspace-records-selected-private-footer.png'))


def journey_producers():
    """Bind ASCII fixture titles to the inspected, pinned Playwright 1.58.2 algorithm."""
    root = Path(__file__).resolve().parents[2] / 'react-app'
    packages = json.loads((root / 'package-lock.json').read_text())['packages']
    for package in ['@playwright/test', 'playwright', 'playwright-core']:
        assert packages['node_modules/' + package]['version'] == '1.58.2'
    rows = []
    for file in ['public-journeys', 'operations-media-journeys', 'workspace-journeys']:
        source = (root / 'e2e/journeys' / (file + '.spec.ts')).read_text()
        assert 'for (const width of [390, 1440])' in source
        tests = list(re.finditer(r"\btest\('([^']+)'", source))
        for index, match in enumerate(tests):
            body = source[match.end():tests[index+1].start() if index+1 < len(tests) else len(source)]
            names = re.findall(r"capture\(page, info, '([^']+)'\)", body)
            names += re.findall(r"info\.outputPath\('([^']+)\.png'\)", body)
            if not names:
                continue
            groups = list(re.finditer(r'test\.describe\(`([^`]+)`', source[:match.start()]))
            for width in ([390, 1440] if groups else [None]):
                prefix = groups[-1][1].replace('${width}', str(width)) + ' ' if groups else ''
                rows.append([file, prefix + match[1], sorted(set(n + '.png' for n in names))])
    source = (root / 'e2e/journeys/password-visibility.spec.ts').read_text()
    assert 'for (const width of [390, 1440])' in source
    assert "test(`password controls ${route} ${width}`" in source
    routes = re.search(r"for \(const route of \[([^]]+)\]", source)[1]
    names = re.findall(r"info\.outputPath\('([^']+\.png)'\)", source)
    for route in re.findall(r"'([^']+)'", routes):
        for width in [390, 1440]:
            rows.append(['password-visibility', f'password controls {route} {width}', names])
    return [[journey_stem(file, title), names] for file, title, names in rows]


def journey_stem(file, title):
    # Playwright 1.58.2 testInfo.js: basename + sanitized title; util.js:
    # windowsFilesystemFriendlyLength=60; 26 prefix + '-' + SHA1[:5] + '-' + 27 suffix.
    # Restrict to this fixture's ASCII titles rather than approximate JS UTF-16 slicing.
    assert file.isascii() and title.isascii()
    sanitized = re.sub(r'[\x00-\x2c\x2e-\x2f\x3a-\x40\x5b-\x60\x7b-\x7f]+', '-', title)
    value = file + '-' + sanitized
    if len(value) <= 60:
        return value
    return value[:26] + '-' + hashlib.sha1(value.encode()).hexdigest()[:5] + '-' + value[-27:]



def setup(tmp_path):
    sources = {suite: tmp_path / suite for suite in collector.SUITES}
    for path in sources.values():
        path.mkdir()
    provenance = {'sourceCommit': 'a' * 40, 'sourceTree': 'b' * 40,
                  'requestedHead': 'c' * 40, 'runId': '123', 'attempt': '1',
                  'outcomes': {suite: 'failure' for suite in collector.SUITES}}
    return sources, tmp_path / 'output', provenance


def put(root, name='volcano-preservation-case-chromium/current-scrollport-top.png', raw=PNG):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def test_exact_bytes_hashes_original_failure_and_missing_capture_visibility(tmp_path):
    sources, output, provenance = setup(tmp_path)
    source = put(sources['volcano'])
    sources['settings'].rmdir()
    collector.stage(sources, output, provenance)
    data = json.loads((output / '00/provenance.json').read_text())
    assert data['outcomes'] == provenance['outcomes']
    assert data['suites']['settings'] == {'sourcePresent': False, 'captures': 0, 'excludedPngCount': 0, 'nativeOutcome': 'failure', 'producerExclusions': [], 'unknownExcludedCount': 0}
    assert data['captureCount'] == 1
    assert data['captures'][0]['sourceRoot'] == 'volcano'
    assert data['captures'][0]['role'] == 'current-diagnostic'
    assert data['captures'][0]['sha256'] == hashlib.sha256(PNG).hexdigest()
    assert source.read_bytes() == (output / '00' / data['captures'][0]['path']).read_bytes() == PNG
    assert len(list(output.iterdir())) == 1
    assert data['shards'] == 1  # No artificial empty parts; suite absence remains in metadata.


def test_private_unexpected_json_video_and_png_excluded(tmp_path):
    sources, output, provenance = setup(tmp_path)
    for name in ['private.json', 'trace.zip', 'video.webm', 'private.png']:
        put(sources['volcano'], 'volcano-preservation-case-chromium/' + name)
    put(sources['volcano'], 'unrelated-private-case/page.png')
    collector.stage(sources, output, provenance)
    assert not list(output.rglob('*.png'))
    assert len(list(output.rglob('*.json'))) == 1


@pytest.mark.parametrize('kind', ['file', 'directory', 'source'])
def test_symlink_rejected(tmp_path, kind):
    sources, output, provenance = setup(tmp_path)
    target = tmp_path / 'private'
    target.mkdir()
    if kind == 'source':
        sources['volcano'].rmdir()
        sources['volcano'].symlink_to(target, target_is_directory=True)
    elif kind == 'directory':
        (sources['volcano'] / 'volcano-preservation-case').symlink_to(target, target_is_directory=True)
    else:
        path = put(sources['volcano'])
        path.unlink()
        path.symlink_to(target)
    with pytest.raises(ValueError, match='symlink' if kind == 'source' else 'incomplete'):
        collector.stage(sources, output, provenance)
    assert not list(output.rglob('*.png'))
    if kind != 'source':
        assert json.loads((output/'00/provenance.json').read_text())['packagingComplete'] is False


def test_limits_split_without_truncation_and_reject_excess(tmp_path, monkeypatch):
    sources, output, provenance = setup(tmp_path)
    monkeypatch.setattr(collector, 'BUDGET', len(PNG))
    put(sources['volcano'])
    put(sources['volcano'], 'volcano-preservation-case-chromium/current-scrollport-footer.png')
    collector.stage(sources, output, provenance)
    assert len(list(output.rglob('*.png'))) == 2
    assert len(list((output / '00').rglob('*.png'))) == 1
    assert len(list((output / '01').rglob('*.png'))) == 1
    monkeypatch.setattr(collector, 'SLOTS', 1)
    with pytest.raises(ValueError, match='incomplete'):
        collector.stage(sources, tmp_path / 'excess', provenance)
    assert not list((tmp_path/'excess').rglob('*.png'))
    assert not json.loads((tmp_path/'excess/00/provenance.json').read_text())['packagingComplete']


def test_oversized_invalid_and_traversal_rejected(tmp_path, monkeypatch):
    sources, output, provenance = setup(tmp_path)
    put(sources['volcano'], raw=b'not a PNG')
    with pytest.raises(ValueError, match='incomplete'):
        collector.stage(sources, output, provenance)
    monkeypatch.setattr(collector, 'BUDGET', 1)
    with pytest.raises(ValueError, match='incomplete'):
        collector.stage(sources, output.with_name('oversized'), provenance)
    with pytest.raises(ValueError, match='traversal'):
        collector.stage(sources, tmp_path / '..' / 'escape', provenance)


def test_known_producers_allowed():
    examples = {'layout': ('representative-case-chromium', 'viewport.png'),
                'volcano': ('volcano-preservation-case-chromium', 'movement-compact-0.5.png'),
                'settings': ('settings-release-case-webkit-mobile', 'settings-release-before-axe.png'),
                'workspace': ('workspace-release-workspac-92e7c-ponsive-and-visually-stable-chromium-high-contrast', 'workspace-records-chromium-high-contrast-diff.png')}
    for suite, parts in examples.items():
        assert collector.allowed(suite, Path(*parts))


def test_journey_literal_captures_match_exact_current_producers():
    rows = journey_producers()
    expected = {stem: frozenset(names) for stem, names in rows}
    assert len(expected) == len(rows)  # No title/width directory collisions.
    assert expected == collector.JOURNEY_CAPTURES
    for stem, names in rows:
        for project in ['chromium', 'firefox', 'webkit']:
            for name in names:
                assert collector.allowed('journeys', Path(stem + '-' + project) / name)
                assert not collector.allowed('layout', Path(stem + '-' + project) / name)
                assert not collector.allowed('journeys', Path(stem + '-unknown') / name)
                assert not collector.allowed('journeys', Path('private-' + stem + '-' + project) / name)
                assert not collector.allowed('journeys', Path(stem + '-' + project) / 'private.png')
                assert not collector.allowed('journeys', Path(stem + '-' + project) / 'nested' / name)
    password = next(stem for stem in expected if stem.startswith('password-visibility-'))
    assert not collector.allowed('journeys', Path(password + '-chromium') / 'contact-failed.png')
    contact = next(stem for stem, names in expected.items() if 'contact-failed.png' in names)
    assert not collector.allowed('journeys', Path(contact + '-chromium') / 'invitation-accepted.png')


def test_journey_producer_contract_needs_no_installed_frontend_or_subprocess(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / 'react-app'
    isolated = tmp_path / 'repo'
    frontend = isolated / 'react-app'
    fixtures = frontend / 'e2e/journeys'
    fixtures.mkdir(parents=True)
    for name in ['public-journeys', 'operations-media-journeys', 'workspace-journeys', 'password-visibility']:
        (fixtures / f'{name}.spec.ts').write_bytes((source / f'e2e/journeys/{name}.spec.ts').read_bytes())
    (frontend / 'package-lock.json').write_bytes((source / 'package-lock.json').read_bytes())
    monkeypatch.setitem(journey_producers.__globals__, '__file__', str(isolated / 'scripts/tests/test_shell_png_evidence.py'))
    def forbidden(*args, **kwargs):
        raise AssertionError('producer source contract must not launch a subprocess')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    assert not (frontend / 'node_modules').exists()
    assert dict((stem, frozenset(names)) for stem, names in journey_producers()) == collector.JOURNEY_CAPTURES


@pytest.mark.parametrize(('file', 'title', 'stem'), [
    ('password-visibility', 'password controls /login 390', 'password-visibility-password-controls-login-390'),
    ('password-visibility', 'password controls /reset-password?token=synthetic-only 390',
     'password-visibility-passwo-3d2f7-rd-token-synthetic-only-390'),
    ('public-journeys', 'public journeys 390px contact missing service fails visibly and retry sends exactly once',
     'public-journeys-public-jou-844ca-nd-retry-sends-exactly-once'),
])
def test_pinned_directory_examples(file, title, stem):
    assert journey_stem(file, title) == stem


def test_journey_new_outputs_retain_exact_bytes_without_disclosing_unknown_names(tmp_path):
    sources, output, provenance = setup(tmp_path)
    original = {}
    for stem, names in journey_producers():
        for name in names:
            path = put(sources['journeys'], stem + '-chromium/' + name)
            original[path.relative_to(sources['journeys']).as_posix()] = path.read_bytes()
    put(sources['journeys'], 'private-sensitive-case/private-person.png')
    collector.stage(sources, output, provenance)
    receipts = [json.loads(path.read_text()) for path in output.rglob('provenance.json')]
    captures = [row for receipt in receipts for row in receipt['captures']]
    assert len(captures) == len(original)
    for row in captures:
        name = row['path'].removeprefix('journeys/')
        assert row['sha256'] == hashlib.sha256(original[name]).hexdigest()
        copies = list(output.glob('*/' + row['path']))
        assert len(copies) == 1 and copies[0].read_bytes() == original[name]
        assert (sources['journeys'] / name).read_bytes() == original[name]
    assert receipts[0]['suites']['journeys']['unknownExcludedCount'] == 1
    assert 'private-person' not in json.dumps(receipts)
    assert 'private-sensitive' not in json.dumps(receipts)


def test_workflow_preserves_original_suites_artifacts_and_failure_status():
    root = Path(__file__).resolve().parents[2]
    text = (root / '.github/workflows/ci-frontend.yml').read_text()
    steps = yaml.safe_load(text)['jobs']['frontend']['steps']
    stage = next(s for s in steps if s.get('id') == 'shell_png')
    assert stage['if'].startswith('always()')
    assert stage['run'] == 'python3 -m scripts.python.shell_png_evidence'
    assert len(stage['env']) == 6
    upload = next(s for s in steps if s.get('name') == 'Retain bounded shell PNG parts')
    assert upload['if'] == "always() && steps.scope.outputs.mode == 'full' && steps.shell_png.outputs.upload_ready == 'true'"
    assert upload['uses'] == './.artifacts/shell-upload-action'
    for identity in ['layout_acceptance', 'volcano_acceptance', 'settings_acceptance', 'workspace_acceptance', 'journeys_acceptance']:
        step = next(s for s in steps if s.get('id') == identity)
        assert 'continue-on-error' not in step
        assert '--grep' not in step['run'] and '--project' not in step['run']
    assert any(s.get('id') == 'browser_acceptance' for s in steps)
    for name in ['layout-109', 'settings-121', 'workspace-124']:
        assert any(s.get('with', {}).get('name') == name for s in steps)
    assert collector.BUDGET + collector.MAX_METADATA < 30 * 1024 * 1024

@pytest.mark.parametrize('width', [390, 1440])
@pytest.mark.parametrize('state', ['home', 'left', 'right', 'palette'])
@pytest.mark.parametrize('role', ['actual', 'expected', 'diff'])
def test_approved_volcano_comparison_producer_names(width, state, role):
    path = Path('volcano-preservation-approved-reference-chromium') / f'volcano-{width}-{state}-{role}.png'
    assert collector.allowed('volcano', path)
    assert collector.image_role(path.name) == f'comparison-{role}'
    assert not collector.allowed('settings', path)
    assert not collector.allowed('volcano', path.with_name('volcano-999-private-actual.png'))

def test_failure_diagnostic_is_not_a_comparison_actual():
    assert collector.image_role('test-failed-1.png') == 'failure-diagnostic'
    assert collector.image_role('workspace-records-post-assert.png') == 'current-diagnostic'


def test_dynamic_upload_is_exact_pinned_bounded_and_rejects_extra_files(tmp_path, monkeypatch):
    sources, _, provenance = setup(tmp_path)
    put(sources['volcano'])
    monkeypatch.chdir(tmp_path)
    output = Path('.artifacts/shell-png')
    collector.stage(sources, output, provenance)
    destination = Path('.artifacts/shell-upload-action')
    collector.upload_action(output, destination)
    action = json.loads((destination / 'action.yml').read_text())
    assert len(action['runs']['steps']) == 1
    step = action['runs']['steps'][0]
    assert step['uses'] == 'actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f'
    assert step['if'] == 'always()' and step['with']['compression-level'] == 0
    assert step['with']['path'] == '.artifacts/shell-png/00/'
    import shutil
    shutil.rmtree(destination)
    (output / '00/private.txt').write_text('excluded synthetic negative marker')
    with pytest.raises(ValueError, match='unexpected shell upload content'):
        collector.upload_action(output, destination)


def test_known_attachment_exclusions_disclose_only_safe_producer_names(tmp_path):
    sources, output, provenance = setup(tmp_path)
    put(sources['layout'], 'route-families-unit-chromium/attachments/Rendered-page-' + 'a'*40 + '.png')
    put(sources['layout'], 'route-families-unit-chromium/attachments/private-name.png')
    collector.stage(sources, output, provenance)
    state=json.loads((output/'00/provenance.json').read_text())['suites']['layout']
    assert state['excludedPngCount']==2 and state['unknownExcludedCount']==1
    assert len(state['producerExclusions'])==1
    assert 'private-name' not in json.dumps(state)


@pytest.mark.parametrize('name', ['contact-received-390','search-paginated-1440'])
@pytest.mark.parametrize('role', ['actual','expected','diff'])
def test_exact_journey_comparisons_are_retained_without_generic_png_expansion(name, role):
    assert collector.allowed('journeys',Path('public-journeys-public-jou-unit')/f'{name}-{role}.png')
    assert not collector.allowed('journeys',Path('private-case')/f'{name}-{role}.png')
    assert not collector.allowed('journeys',Path('public-journeys-public-jou-unit/private.png'))


def test_parts_split_whole_members_and_total_budget_fails_honestly(tmp_path, monkeypatch):
    sources, output, provenance = setup(tmp_path)
    for i in range(3):
        put(sources['volcano'], f'volcano-preservation-unit-{i}/page.png')
    monkeypatch.setattr(collector, 'BUDGET', len(PNG)*2)
    collector.stage(sources, output, provenance)
    assert len(list(output.iterdir()))==2
    rows=[r for p in output.rglob('provenance.json') for r in json.loads(p.read_text())['captures']]
    assert len(rows)==3 and len({r['path'] for r in rows})==3
    assert all(r['sha256']==hashlib.sha256(PNG).hexdigest() for r in rows)
    monkeypatch.setattr(collector, 'TOTAL_BYTES', len(PNG)*2)
    with pytest.raises(ValueError,match='incomplete'):
        collector.stage(sources, output.with_name('too-large'), provenance)


def test_more_than_one_hundred_parts_are_uploaded_in_numeric_order(tmp_path, monkeypatch):
    sources, _, provenance = setup(tmp_path)
    for index in range(101):
        put(sources['volcano'], f'volcano-preservation-unit-{index}/page.png')
    monkeypatch.setattr(collector, 'BUDGET', len(PNG))
    monkeypatch.chdir(tmp_path)
    output=Path('.artifacts/shell-png')
    collector.stage(sources,output,provenance)
    destination=Path('.artifacts/shell-upload-action')
    collector.upload_action(output,destination)
    steps=json.loads((destination/'action.yml').read_text())['runs']['steps']
    assert len(steps)==101
    assert [s['with']['path'] for s in steps]==[f'.artifacts/shell-png/{i:02}/' for i in range(101)]


def test_partial_safe_producers_upload_but_packaging_stays_fatal(tmp_path, monkeypatch):
    sources, _, provenance = setup(tmp_path)
    good = put(sources['volcano'], 'volcano-preservation-good/page.png')
    put(sources['volcano'], 'volcano-preservation-rejected-private/page.png', b'unsafe invalid bytes')
    monkeypatch.chdir(tmp_path)
    output = Path('.artifacts/shell-png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    collector.upload_action(output, Path('.artifacts/shell-upload-action'))
    receipt = json.loads((output/'00/provenance.json').read_text())
    assert receipt['packagingComplete'] is False
    assert receipt['packagingErrors'] == [{'scope': 'volcano', 'rejectedProducerCount': 1}]
    assert len(receipt['captures']) == 1
    assert (output/'00'/receipt['captures'][0]['path']).read_bytes() == good.read_bytes()
    assert 'rejected-private' not in json.dumps(receipt)
    assert 'unsafe invalid bytes' not in json.dumps(receipt)


def test_overflow_keeps_whole_valid_producer_with_explicit_failure(tmp_path, monkeypatch):
    sources, output, provenance = setup(tmp_path)
    for name in ['a', 'b']:
        put(sources['volcano'], f'volcano-preservation-{name}/page.png')
    monkeypatch.setattr(collector, 'TOTAL_BYTES', len(PNG))
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    receipt=json.loads((output/'00/provenance.json').read_text())
    assert not receipt['packagingComplete']
    assert receipt['packagingErrors'] == [{'scope':'budget','rejectedProducerCount':1}]
    assert len(receipt['captures']) == 1 and len(list(output.rglob('*.png'))) == 1


def test_invalid_receipt_rejects_whole_producer_without_stranding_valid_evidence(tmp_path):
    sources, output, provenance = setup(tmp_path)
    put(sources['volcano'], 'volcano-preservation-good/page.png')
    put(sources['volcano'], 'volcano-preservation-bad/page.png')
    put(sources['volcano'], 'volcano-preservation-bad/continuous-current.json', b'{"private":"not a receipt"}')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    receipt=json.loads((output/'00/provenance.json').read_text())
    assert not receipt['packagingComplete'] and len(receipt['captures']) == 1
    assert 'good/page.png' in receipt['captures'][0]['path']
    assert not list(output.rglob('continuous-current.json'))
    assert 'private' not in json.dumps(receipt)


def test_serialized_metadata_partitions_without_losing_capture_rows(tmp_path, monkeypatch):
    sources, output, provenance = setup(tmp_path)
    for i in range(24):
        put(sources['volcano'], f'volcano-preservation-{i:03}-' + 'x'*160 + '/page.png')
    monkeypatch.setattr(collector, 'MAX_METADATA', 5000)
    collector.stage(sources, output, provenance)
    receipts = list(output.rglob('provenance.json'))
    assert len(receipts) > 1
    assert all(p.stat().st_size <= 5000 for p in receipts)
    rows = [r for p in receipts for r in json.loads(p.read_text())['captures']]
    assert len(rows) == len({r['path'] for r in rows}) == 24


@pytest.mark.parametrize("exclusion_count", [9, 24])
def test_exclusion_detail_overflow_keeps_images_and_explicit_fatal_count(tmp_path, monkeypatch, exclusion_count):
    sources, _, provenance = setup(tmp_path)
    put(sources['volcano'], 'volcano-preservation-good/page.png')
    for i in range(exclusion_count):
        put(sources['volcano'], f'volcano-preservation-{i:03}-' + 'x'*150 + '/attachments/page-' + 'a'*40 + '.png')
    monkeypatch.setattr(collector, 'MAX_METADATA', 5000)
    monkeypatch.chdir(tmp_path)
    output = Path('.artifacts/shell-png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    collector.upload_action(output, Path('.artifacts/shell-upload-action'))
    receipt = json.loads((output/'00/provenance.json').read_text())
    assert receipt['suites']['volcano']['omittedProducerExclusionCount'] == exclusion_count
    assert receipt['suites']['volcano']['excludedPngCount'] == exclusion_count
    assert not receipt['packagingComplete'] and len(receipt['captures']) == 1


def test_null_registered_journey_receipt_keeps_valid_producer(tmp_path, monkeypatch):
    sources, _, provenance = setup(tmp_path)
    put(sources['journeys'], 'public-journeys-public-jou-good/contact-received-390-actual.png')
    put(sources['journeys'], 'public-journeys-public-jou-bad/sequence-journey-contact-received.json', b'null')
    monkeypatch.chdir(tmp_path)
    output = Path('.artifacts/shell-png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    collector.upload_action(output, Path('.artifacts/shell-upload-action'))
    receipt=json.loads((output/'00/provenance.json').read_text())
    assert not receipt['packagingComplete'] and len(receipt['captures']) == 1
    assert not list(output.rglob('sequence-*.json'))


def test_workspace_pairs_reject_unknown_project_text_and_cross_pair_images():
    from scripts.python import workspace_ownership
    first = workspace_ownership.CASES['records-schema'] + '-chromium-compact'
    second = workspace_ownership.CASES['imports-exports'] + '-chromium-compact'
    assert collector.allowed('workspace', Path(first, 'workspace-records-chromium-compact-actual.png'))
    assert collector.allowed('workspace', Path(second, 'workspace-imports-post-assert.png'))
    for name in ['workspace-records-private-client-name-actual.png',
                 'workspace-records-firefox-desktop-actual.png',
                 'workspace-imports-chromium-compact-actual.png',
                 'current-continuous-workspace-exports-000.png']:
        assert not collector.allowed('workspace', Path(first, name))


def test_workspace_continuous_rejects_wrong_project_with_same_title_and_state(tmp_path):
    import hashlib

    from scripts.python import workspace_ownership

    sources, output, provenance = setup(tmp_path)
    case = workspace_ownership.CASES['imports-exports'] + '-webkit-mobile'
    folder = sources['workspace'] / case
    folder.mkdir()
    image = 'current-continuous-current-000.png'
    raw = b'\x89PNG\r\n\x1a\nsynthetic fixture'
    (folder / image).write_bytes(raw)
    data = dict(schemaVersion=1, fixtureScope='synthetic-project-tests',
                scope='Diagnostic continuous viewports; not visual acceptance.',
                sourceCommit=provenance['sourceCommit'], sourceTree=provenance['sourceTree'],
                runId=str(provenance['runId']), attempt=str(provenance['attempt']),
                project='chromium-compact', test=workspace_ownership.TITLES['imports-exports'],
                route='/workspace', state='current', target='content-scrollport', extent=400,
                segmentLimit=64, reachedEnd=True, complete=True, errors=[],
                segments=[dict(index=0, route='/workspace', start=0, end=400, extent=400,
                               offset=0, max=0, height=400, inset=0, scale=1,
                               viewport=[390,844,3], rect=[0,0,390,400], file=image,
                               sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))])
    (folder / 'continuous-current.json').write_text(json.dumps(data))
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    assert not list(output.rglob('continuous-current.json'))
    # Correct binding is retained without rewriting the original failure output.
    data['project'] = 'webkit-mobile'
    (folder / 'continuous-current.json').write_text(json.dumps(data))
    collector.stage(sources, tmp_path / 'corrected-output', provenance)
    assert len(list((tmp_path / 'corrected-output').rglob('continuous-current.json'))) == 1


def test_exact_confirmation_attempt_producers_do_not_broaden_collection():
    case = 'workspace-release-workspac-c3eae-ons-cancel-without-mutation-chromium-compact'
    for state in ('submit-review', 'publish', 'delete', 'restore'):
        name = f'workspace-confirm-{state}-attempt.png'
        assert collector.allowed('workspace', Path(case) / name)
        assert collector.image_role(name) == 'current-diagnostic'
        assert not collector.allowed('workspace', Path('workspace-release-selected-9c572-aves-or-discards-explicitly-chromium-compact') / name)
    for name in ('workspace-confirm-arbitrary-attempt.png', 'workspace-confirm-delete-expected.png', 'private.png'):
        assert not collector.allowed('workspace', Path(case) / name)


def test_confirmation_native_coverage_retains_attempt_before_focus_and_never_confirms():
    source = (Path(__file__).resolve().parents[2] / 'react-app/e2e/workspace/workspace-release.spec.ts').read_text()
    case = source.split("test('workspace workflow confirmations cancel without mutation'", 1)[1].split('declare global', 1)[0]
    assert "['submit-review', 'Submit for review', 'Keep unchanged', 'Confirm action']" in case
    assert "['restore', 'Restore', 'Keep current', 'Confirm restore']" in case
    assert case.index('captureAttempted = true') < case.index('await ownershipStep(() => captureConfirmation(page, testInfo, state))')
    helper = (Path(__file__).resolve().parents[2] / 'react-app/e2e/workspace/confirmation-capture.ts').read_text()
    assert helper.index('settlement = await settleConfirmation') < helper.index('const raw = await ownedScreenshot')
    assert helper.index('const raw = await ownedScreenshot') < helper.index("fail('capture-state-invalid'")
    assert 'sha256: createHash' in helper and 'post = await measure(page)' in helper
    assert 'if (failed) throw failure' in helper
    assert case.index('await ownershipStep(capture);') < case.index('expect(dialog.getByRole')
    assert "toBeInViewport({ ratio: 1 })" in case
    assert "page.keyboard.press('Escape')" in case
    assert 'metric.available >= metric.required' in case
    assert 'expect(trigger).toBeFocused()' in case
    assert 'expect(confirmationRequests.get(page)!.mutations).toBe(0)' in case
    assert "name: confirm, exact: true })).toBeEnabled()" in case
    assert "name: confirm, exact: true }).click()" not in case
    assert 'await ownershipCleanup' in case and 'if (!failed)' in case and 'if (failed) throw failure' in case


def test_movement_transition_capture_exact_producer_and_state():
    from scripts.python.shell_png_evidence import allowed
    for scenario in ('compact','landscape','desktop','rtl','rtl-large-text','forced','zoom'):
        case = f'volcano-preservation-reserved-movement-space-{scenario}-chromium'
        for state in ('before-disable','after-disable','after-enable-before-close','after-close'):
            name = f'movement-transition-{scenario}-{state}.png'
            assert allowed('volcano', Path(case)/name)
            assert not allowed('workspace', Path(case)/name)
            assert not allowed('volcano', Path('private')/name)
        assert not allowed('volcano', Path(case)/f'movement-transition-{scenario}-private.png')
