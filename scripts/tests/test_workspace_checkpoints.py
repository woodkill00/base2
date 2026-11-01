import copy
import json
from pathlib import Path

import pytest

from scripts.python import workspace_checkpoints as module


def event():
    return dict(phase='continuous-footer-before', state='workspace-exports', index=-1, focus='neutral', elapsedMs=10,
                phaseElapsedMs=2, errorCounts=dict(total=1, timeout=1, comparison=0),
                route='workspace', activeState='exports', target='element', targetCount=1,
                dialogCount=0, offset=900, max=900, viewport=[390, 844],
                visualViewport=[0, 0, 390, 844, 1], targetRect=[0, 0, 390, 700],
                footerRect=[0, 600, 390, 100], headerRect=[0, 0, 390, 80])


def receipt():
    return dict(schemaVersion=1, scope='synthetic-workspace-webkit', incomplete=False, events=[event()])


def test_roundtrip_and_boundaries():
    data = receipt()
    assert module.validate(json.dumps(data).encode()) == data
    data['events'][0]['offset'] = -12
    assert module.validate(json.dumps(data).encode()) == data
    data['events'] *= 192
    module.validate(json.dumps(data).encode())
    data['events'].append(event())
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode())


@pytest.mark.parametrize('bad', [None, [], True, {'private': 'text'}, 'secret'])
def test_reject_root(bad):
    with pytest.raises(ValueError):
        module.validate(json.dumps(bad).encode())


@pytest.mark.parametrize('key,value', [('phase', 'private'), ('route', '/customer/123'),
    ('state', 'private'), ('activeState', 'customer'), ('target', 'unknown'),
    ('elapsedMs', -1), ('max', float('inf')), ('offset', True), ('targetCount', 2),
    ('footerRect', [0, 0, -1, 1]), ('visualViewport', [0, 0, 1, 1, 0]),
    ('viewport', [0, 844]), ('errorCounts', {'total': 1, 'timeout': 2, 'comparison': 0})])
def test_reject_bad_event(key, value):
    data = receipt()
    data['events'][0][key] = value
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode())


def test_reject_extra_private_and_size():
    data = receipt()
    data['events'][0]['message'] = 'not allowed'
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode())
    with pytest.raises(ValueError):
        module.validate(b' ' * 131073)
    data = receipt()
    second = copy.deepcopy(event())
    second['elapsedMs'] = 1
    data['events'].append(second)
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode())


def test_exact_producer_only():
    case = 'workspace-release-workspac-d0657-ponsive-and-visually-stable-webkit-mobile'
    assert module.registered('workspace', Path(case) / module.NAME)
    for suite, path in [('media', Path(case) / module.NAME), ('workspace', Path(case + '-retry1') / module.NAME),
                        ('workspace', Path(case) / 'private.json'), ('workspace', Path('other') / module.NAME),
                        ('workspace', Path(case) / '..' / module.NAME)]:
        assert not module.registered(suite, path)


def test_transport_retains_exact_diagnostic_with_role_and_rejects_private_payload(tmp_path):
    from scripts.python import shell_png_evidence as collector
    from scripts.tests.test_shell_png_evidence import setup
    sources, output, provenance = setup(tmp_path)
    folder = sources['workspace'] / 'workspace-release-workspac-d0657-ponsive-and-visually-stable-webkit-mobile'
    folder.mkdir(parents=True)
    path = folder / module.NAME
    raw = json.dumps(receipt()).encode()
    path.write_bytes(raw)
    collector.stage(sources, output, provenance)
    data = json.loads((output / '00/provenance.json').read_bytes())
    row = next(row for row in data['diagnostics'] if row['path'].endswith(module.NAME))
    assert row['role'] == 'workspace-phase-diagnostic'
    assert (output / '00' / row['path']).read_bytes() == raw
    assert row['sourceRoot'] == 'workspace'


def test_checkpoint_hooks_preserve_footer_assertion_and_capture_first():
    root = Path(__file__).resolve().parents[2]
    source = (root / 'react-app/e2e/continuous-scroll.ts').read_text()
    assert source.index("'capture-before', index") < source.index("'capture-after', index")
    assert source.index("'capture-after', index") < source.index('Capture endpoint scroll/focus/geometry must remain stable')
    assert "await expect(page.locator('.volcano-footer-frame')).toBeInViewport();" in source
    assert source.index("'continuous-footer-before'") < source.index("await expect(page.locator('.volcano-footer-frame')).toBeInViewport();")
    assert "failure = error;\n    errors.push('capture-or-validation-failed');" in source


def test_mixed_invalid_receipt_preserves_other_producer_and_fails(tmp_path):
    from scripts.python import shell_png_evidence as collector
    from scripts.tests.test_shell_png_evidence import put, setup
    sources, output, provenance = setup(tmp_path)
    folder = sources['workspace'] / 'workspace-release-workspac-d0657-ponsive-and-visually-stable-webkit-mobile'
    folder.mkdir(parents=True)
    (folder / module.NAME).write_text(json.dumps(receipt()).replace('"scope": "synthetic-workspace-webkit"', '"scope": "secret", "scope": "synthetic-workspace-webkit"'))
    put(sources['layout'], 'representative-safe/page.png')
    with pytest.raises(collector.PackagingIncomplete):
        collector.stage(sources, output, provenance)
    data = json.loads((output / '00/provenance.json').read_bytes())
    assert data['packagingComplete'] is False
    assert len(data['captures']) == 1
    assert not data['diagnostics']
    assert not any(p.name == module.NAME for p in output.rglob('*'))
    assert 'secret' not in (output / '00/provenance.json').read_text()


@pytest.mark.parametrize('key,value', [('scope', 'synthetic-workspace-webkit'), ('route', 'workspace')])
def test_duplicate_keys_reject_original_raw_payload(key, value):
    raw = json.dumps(receipt()).replace(f'"{key}": "{value}"', f'"{key}": "PRIVATE", "{key}": "{value}"').encode()
    # Ordinary json.loads accepts this and hides the first value; raw transport must not.
    assert 'PRIVATE' not in json.dumps(json.loads(raw))
    with pytest.raises(ValueError):
        module.validate(raw)
