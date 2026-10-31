"""Regressions for native build inputs and truthful imported scanner evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from api.tests import media_inspector_build_inputs as build


def test_download_rejects_hash_mismatch(tmp_path):
    with patch.object(build.urllib.request, 'urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = b'wrong'
        with pytest.raises(ValueError, match='digest'):
            build.download_verified('https://example.invalid/source', '0' * 64, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_download_accepts_exact_bytes(tmp_path):
    payload = b'verified fixture'
    with patch.object(build.urllib.request, 'urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = payload
        build.download_verified('https://example.invalid/source', hashlib.sha256(payload).hexdigest(), tmp_path / 'out')
    assert (tmp_path / 'out').read_bytes() == payload


def scanner_fixture(tmp_path):
    files = {name: name.encode() for name in build.SCANNER_FILES}
    evidence = {}
    for name, payload in files.items():
        path = tmp_path / name.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        evidence[name] = hashlib.sha256(payload).hexdigest()
    provenance = tmp_path / 'usr/local/share/base2/clamav'
    provenance.mkdir(parents=True)
    (provenance / 'control').write_text('Package: clamav\nVersion: 1.5.4-1\n')
    (provenance / 'files.json').write_text(json.dumps(evidence))
    return {'clamav': {'version': '1.5.4', 'packageVersion': '1.5.4-1',
                       'url': 'https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.4/clamav-1.5.4.linux.x86_64.deb',
                       'sha256': 'a' * 64}}, provenance


def test_scanner_bom_keeps_upstream_identity_original_control_and_file_hashes(tmp_path):
    lock, provenance = scanner_fixture(tmp_path)
    with patch.object(build.subprocess, 'check_output', return_value=b'ClamAV 1.5.4/28111/test\n'):
        bom = build.scanner_bom(lock, root=tmp_path)
    upstream, archive = bom['components']
    assert upstream['purl'] == 'pkg:generic/clamav@1.5.4'
    assert upstream['cpe'] == 'cpe:2.3:a:clamav:clamav:1.5.4:*:*:*:*:*:*:*'
    assert archive['hashes'] == [{'alg': 'SHA-256', 'content': 'a' * 64}]
    assert archive['version'] == '1.5.4-1'
    properties = {item['name']: item['value'] for item in upstream['properties']}
    for name, digest in json.loads((provenance / 'files.json').read_text()).items():
        assert properties[f'base2:file:sha256:{name}'] == digest
    assert properties['base2:source:controlSha256'] == hashlib.sha256((provenance / 'control').read_bytes()).hexdigest()


@pytest.mark.parametrize('defect', ('binary', 'version', 'control'))
def test_scanner_bom_rejects_unbound_payload_or_false_version(tmp_path, defect):
    lock, provenance = scanner_fixture(tmp_path)
    version = b'ClamAV 1.5.4\n'
    if defect == 'binary':
        (tmp_path / 'usr/bin/clamscan').write_bytes(b'changed')
    elif defect == 'version':
        version = b'ClamAV 1.5.2\n'
    else:
        (provenance / 'control').write_text('Package: clamav\nVersion: 1.5.2-1\n')
    with patch.object(build.subprocess, 'check_output', return_value=version), pytest.raises(ValueError):
        build.scanner_bom(lock, root=tmp_path)


def test_runtime_lock_has_no_python_apk_or_build_tools():
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / 'media-inspector-runtime.lock.json').read_text())
    runtime = [item for item in lock['apks'] if 'runtime' in item['roles']]
    assert len(runtime) == 21
    assert not any(item['name'].startswith(('python', 'gcc', 'apk-tools', 'busybox', 'build-base')) for item in runtime)
    assert all(len(item['sha256']) == 64 and item['indexChecksum'].startswith('Q1') for item in lock['apks'])
    assert lock['repository']['indexSha256']
    assert lock['patches'][0]['sha256'] and len(lock['patches']) == 2


def test_python_file_manifest_binds_source_patches_and_actual_interpreter(tmp_path):
    executable = tmp_path / 'usr/local/bin/python3.15'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'compiled fixture')
    destination = tmp_path / 'manifest.json'
    lock = {'pythonVersion': '3.15.2', 'source': {'sha256': 'a' * 64}, 'patches': [{'sha256': 'b' * 64}]}
    build.record_python_files(lock, tmp_path, destination)
    manifest = json.loads(destination.read_text())
    assert manifest['source'] == lock['source'] and manifest['patches'] == lock['patches']
    assert manifest['files'] == {'usr/local/bin/python3.15': hashlib.sha256(b'compiled fixture').hexdigest()}


def test_python_file_manifest_rejects_missing_interpreter(tmp_path):
    with pytest.raises(ValueError, match='interpreter'):
        build.record_python_files({}, tmp_path, tmp_path / 'manifest.json')


@pytest.mark.parametrize('changed', (False, True))
def test_prepare_requires_locked_index_entry_and_records_actual_trust_metadata(tmp_path, changed):
    import io
    import tarfile
    payload = b'P:fixture\nV:1-r0\nC:Q1verified\n\n'
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        info = tarfile.TarInfo('APKINDEX')
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    index = stream.getvalue()
    lock = {'repository': {'indexUrl': 'https://example.invalid/index', 'keySha256': 'a' * 64},
            'apks': [{'name': 'fixture', 'version': '1-r0', 'indexChecksum': 'Q1changed' if changed else 'Q1verified',
                      'url': 'https://example.invalid/fixture.apk', 'sha256': 'b' * 64,
                      'filename': 'fixture.apk', 'roles': ['build', 'runtime']}],
            'patches': [{'url': 'https://example.invalid/patch', 'sha256': 'c' * 64, 'filename': 'patch'}]}
    with patch.object(build.urllib.request, 'urlopen') as request, patch.object(build, 'download_verified') as download:
        request.return_value.__enter__.return_value.read.return_value = index
        if changed:
            with pytest.raises(ValueError, match='absent/changed'):
                build.prepare(lock, tmp_path)
            download.assert_not_called()
            return
        build.prepare(lock, tmp_path)
    assert download.call_count == 2
    evidence = json.loads((tmp_path / 'repository-evidence.json').read_text())
    assert evidence['indexSha256'] == hashlib.sha256(index).hexdigest()
    assert evidence['keySha256'] == 'a' * 64
    assert (tmp_path / 'runtime-pins.txt').read_text() == 'fixture=1-r0\n'
    assert (tmp_path / 'build-pins.txt').read_text() == 'fixture=1-r0\n'
