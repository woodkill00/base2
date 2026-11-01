"""Bounded shell collection never mutates test inputs or native outcomes."""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.python import shell_png_evidence as collector

PNG = b'\x89PNG\r\n\x1a\n' + b'unit fixture, not native evidence'


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
    assert data['suites']['settings'] == {'sourcePresent': False, 'captures': 0, 'excludedPngCount': 0, 'nativeOutcome': 'failure'}
    assert data['captureCount'] == 1
    assert data['captures'][0]['sourceRoot'] == 'volcano'
    assert data['captures'][0]['role'] == 'current-diagnostic'
    assert data['captures'][0]['sha256'] == hashlib.sha256(PNG).hexdigest()
    assert source.read_bytes() == (output / '00' / data['captures'][0]['path']).read_bytes() == PNG
    assert len(list(output.iterdir())) == 16
    assert json.loads((output / '15/provenance.json').read_text())['captures'] == []


def test_private_unexpected_json_video_and_png_excluded(tmp_path):
    sources, output, provenance = setup(tmp_path)
    for name in ['private.json', 'trace.zip', 'video.webm', 'private.png']:
        put(sources['volcano'], 'volcano-preservation-case-chromium/' + name)
    put(sources['volcano'], 'unrelated-private-case/page.png')
    collector.stage(sources, output, provenance)
    assert not list(output.rglob('*.png'))
    assert len(list(output.rglob('*.json'))) == 16


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
    with pytest.raises(ValueError, match='symlink'):
        collector.stage(sources, output, provenance)
    assert not output.exists()


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
    with pytest.raises(ValueError, match='capacity'):
        collector.stage(sources, tmp_path / 'excess', provenance)
    assert not (tmp_path / 'excess').exists()


def test_oversized_invalid_and_traversal_rejected(tmp_path, monkeypatch):
    sources, output, provenance = setup(tmp_path)
    put(sources['volcano'], raw=b'not a PNG')
    with pytest.raises(ValueError, match='signature'):
        collector.stage(sources, output, provenance)
    monkeypatch.setattr(collector, 'BUDGET', 1)
    with pytest.raises(ValueError, match='oversized'):
        collector.stage(sources, output, provenance)
    with pytest.raises(ValueError, match='traversal'):
        collector.stage(sources, tmp_path / '..' / 'escape', provenance)


def test_known_producers_allowed():
    examples = {'layout': ('representative-case-chromium', 'viewport.png'),
                'volcano': ('volcano-preservation-case-chromium', 'movement-compact-0.5.png'),
                'settings': ('settings-release-case-webkit-mobile', 'settings-release-before-axe.png'),
                'workspace': ('workspace-release-case-chromium-high-contrast', 'workspace-records-chromium-high-contrast-diff.png')}
    for suite, parts in examples.items():
        assert collector.allowed(suite, Path(*parts))


def test_workflow_preserves_original_suites_artifacts_and_failure_status():
    root = Path(__file__).resolve().parents[2]
    text = (root / '.github/workflows/ci-frontend.yml').read_text()
    steps = yaml.safe_load(text)['jobs']['frontend']['steps']
    stage = next(s for s in steps if s.get('id') == 'shell_png')
    assert stage['if'].startswith('always()')
    assert stage['run'] == 'python3 -m scripts.python.shell_png_evidence'
    assert len(stage['env']) == 5
    uploads = [s for s in steps if s.get('name', '').startswith('Retain bounded shell PNG shard')]
    assert len(uploads) == 16
    for index, step in enumerate(uploads):
        assert step['if'] == "always() && steps.scope.outputs.mode == 'full' && steps.shell_png.outcome == 'success'"
        assert step['with']['path'] == f'.artifacts/shell-png/{index:02}/'
        assert step['with']['compression-level'] == 0
        assert step['with']['if-no-files-found'] == 'error'
    for identity in ['layout_acceptance', 'volcano_acceptance', 'settings_acceptance', 'workspace_acceptance']:
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
