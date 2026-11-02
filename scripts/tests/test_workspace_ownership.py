"""Strict transport of original lease receipts and completed partial frames."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.python import shell_png_evidence as collector
from scripts.python import workspace_ownership as module

CASE = 'workspace-release-workspac-d0657-ponsive-and-visually-stable-webkit-mobile'
PNG = b'\x89PNG\r\n\x1a\nsynthetic fixture only'


def fixture(tmp_path):
    directory = tmp_path / CASE
    directory.mkdir(parents=True)
    frame = 'current-continuous-workspace-exports-004.png'
    (directory / frame).write_bytes(PNG)
    provenance = dict(sourceCommit='a'*40, sourceTree='b'*40, runId='123', attempt='1')
    data = dict(schemaVersion=1, scope='synthetic-workspace-ownership', scenario='corpus', **provenance,
                revoked=True, bodySettled=False, hookStarted=True, incomplete=True,
                coverage={k: 'incomplete' for k in module.STATES['corpus']}, errors=['no-quiescence'],
                frames=[dict(file=frame, sha256=hashlib.sha256(PNG).hexdigest(), bytes=len(PNG))])
    path = directory / module.NAME
    path.write_text(json.dumps(data))
    return path, data, provenance


def test_incomplete_original_frame_roundtrip(tmp_path):
    path, data, provenance = fixture(tmp_path)
    assert module.registered('workspace', Path(CASE)/module.NAME)
    assert module.validate(path.read_bytes(), path, provenance) == data
    assert collector.image_role(module.NAME) == 'workspace-ownership-diagnostic'


@pytest.mark.parametrize('value', [None, [], True, 'private', 5])
def test_reject_wrong_root(tmp_path, value):
    path, _, provenance = fixture(tmp_path)
    with pytest.raises(ValueError):
        module.validate(json.dumps(value).encode(), path, provenance)


@pytest.mark.parametrize('key,value', [('sourceTree','c'*40), ('runId','99'), ('scenario','private'),
    ('incomplete',False), ('errors',['arbitrary private message']), ('bodySettled',0), ('coverage',{'private':'complete'}),
    ('hookStarted','true'), ('revoked',False)])
def test_reject_inconsistent_or_private_fields(tmp_path, key, value):
    path, data, provenance = fixture(tmp_path)
    data[key] = value
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode(), path, provenance)


def test_reject_extra_duplicate_bounds_and_frame_tamper(tmp_path):
    path, original, provenance = fixture(tmp_path)
    for change in [dict(private='SECRET'), dict(frames=original['frames']*2),
                   dict(errors=['cancelled','cancelled'])]:
        data = {**original, **change}
        with pytest.raises(ValueError):
            module.validate(json.dumps(data).encode(), path, provenance)
    with pytest.raises(ValueError):
        module.validate(b' ' * (module.BUDGET+1), path, provenance)
    with pytest.raises(ValueError):
        module.validate(path.read_bytes()[:-1]+b',"schemaVersion":1}', path, provenance)
    data = copy.deepcopy(original)
    data['frames'][0]['file'] = '../private.png'
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode(), path, provenance)
    frame = path.parent / original['frames'][0]['file']
    frame.write_bytes(PNG+b'changed')
    with pytest.raises(ValueError):
        module.validate(path.read_bytes(), path, provenance)
    frame.unlink()
    with pytest.raises(ValueError):
        module.validate(path.read_bytes(), path, provenance)
    private = tmp_path / 'private.png'
    private.write_bytes(PNG)
    frame.symlink_to(private)
    with pytest.raises(ValueError):
        module.validate(path.read_bytes(), path, provenance)


def test_bounded_transport_preserves_partial_frames_and_native_failure(tmp_path):
    sources = {name: tmp_path / name for name in collector.SUITES}
    for source in sources.values():
        source.mkdir()
    path, _, provenance = fixture(sources['workspace'])
    provenance.update(requestedHead='c'*40, outcomes={name:'failure' for name in collector.SUITES})
    output = tmp_path / 'output'
    collector.stage(sources, output, provenance)
    meta = json.loads((output/'00/provenance.json').read_text())
    assert meta['outcomes']['workspace'] == 'failure'
    copies = list(output.rglob(module.NAME))
    assert len(copies) == 1 and copies[0].read_bytes() == path.read_bytes()
    assert any(row['role'] == 'workspace-ownership-diagnostic' for row in meta['diagnostics'])
    assert len(list(output.rglob('*.png'))) == 1


def test_wrong_producer_or_project_is_not_exported():
    for case in [CASE+'-private', 'workspace-release-customer-webkit-mobile', CASE.replace('webkit-mobile','untrusted')]:
        assert not module.registered('workspace',Path(case)/module.NAME)
    assert not module.registered('journeys',Path(CASE)/module.NAME)

@pytest.mark.parametrize('scenario,other', [('records-schema', 'workspace-exports'), ('imports-exports', 'workspace-records')])
def test_pair_receipts_bind_exact_case_states_and_reject_other_pair(tmp_path, scenario, other):
    path, data, provenance = fixture(tmp_path)
    target = tmp_path / (module.CASES[scenario] + '-webkit-mobile')
    path.parent.rename(target)
    path = target / module.NAME
    data.update(scenario=scenario, coverage={k: 'incomplete' for k in module.STATES[scenario]}, frames=[])
    assert module.validate(json.dumps(data).encode(), path, provenance) == data
    assert module.state_registered(target.name, 'current')
    assert not module.state_registered(target.name, other)
    data['coverage'][other] = 'complete'
    with pytest.raises(ValueError):
        module.validate(json.dumps(data).encode(), path, provenance)
