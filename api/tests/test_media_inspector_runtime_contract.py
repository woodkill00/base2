"""Negative/positive coverage for fail-closed runtime/SBOM acceptance checks."""
from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from api.tests import media_inspector_runtime_acceptance as runtime
from api.tests.media_inspector_sbom_acceptance import validate_inventory


def complete_inventory():
    import json
    from pathlib import Path
    from api.tests.media_inspector_sbom_acceptance import WHEELS
    from api.tests.media_inspector_build_inputs import SCANNER_FILES
    lock = json.loads((Path(__file__).resolve().parents[1] / 'media-inspector-runtime.lock.json').read_text())
    components = [{'name': 'python', 'version': '3.15.2',
                   'properties': [{'name': 'syft:package:type', 'value': 'binary'}]}]
    for item in lock['apks']:
        if 'runtime' in item['roles']:
            components.append({'name': item['name'], 'version': item['version'],
                               'purl': f'pkg:apk/wolfi/{item["name"]}@{item["version"]}'})
    for name, version in WHEELS.items():
        components.append({'name': name, 'version': version, 'purl': f'pkg:pypi/{name}@{version}'})
    raw = {'components': copy.deepcopy(components)}
    scanner = lock['clamav']
    properties = {'base2:source:archiveSha256': scanner['sha256'],
                  'base2:source:packageVersion': scanner['packageVersion'],
                  'base2:source:controlSha256': 'b' * 64,
                  **{f'base2:file:sha256:{name}': 'a' * 64 for name in SCANNER_FILES}}
    imported = [
        {'name': 'clamav', 'version': '1.5.4', 'purl': 'pkg:generic/clamav@1.5.4',
         'cpe': 'cpe:2.3:a:clamav:clamav:1.5.4:*:*:*:*:*:*:*',
         'properties': [{'name': name, 'value': value} for name, value in properties.items()]},
        {'name': scanner['url'].rsplit('/', 1)[-1], 'version': scanner['packageVersion'],
         'hashes': [{'alg': 'SHA-256', 'content': scanner['sha256']}]},
    ]
    provenance = {'components': imported}
    digest = hashlib.sha256((json.dumps(provenance, sort_keys=True) + '\n').encode()).hexdigest()
    consumed = copy.deepcopy(imported[0])
    consumed['properties'] = [{'name': 'syft:package:foundBy', 'value': 'sbom-cataloger'},
                              {'name': 'syft:location:0:path', 'value': '/usr/local/share/base2/clamav.bom.json'}]
    source_file = {'type': 'file', 'name': '/usr/local/share/base2/clamav.bom.json',
                   'hashes': [{'alg': 'SHA-256', 'content': digest}]}
    return {'components': components + [consumed, source_file]}, raw, provenance, lock, digest


def test_sbom_accepts_real_fixed_binary_and_complete_inventory():
    validate_inventory(*complete_inventory())


@pytest.mark.parametrize('change', ('missing-python', 'old-python', 'fake-pypi-python',
                                  'missing-binary-identity', 'foreign-debian', 'missing-libc',
                                  'missing-clamav', 'wrong-clamav', 'missing-wheel', 'extra-apk',
                                  'old-python-apk', 'wrong-wheel', 'missing-archive', 'changed-archive',
                                  'missing-file-evidence', 'empty-raw', 'missing-source-bom',
                                  'changed-source-bom', 'unconsumed-provenance'))
def test_sbom_rejects_incomplete_or_misleading_inventory(change):
    candidate, raw, provenance, lock, digest = complete_inventory()
    items = candidate['components']
    if change == 'missing-python':
        items.pop(0)
    elif change == 'old-python':
        items[0]['version'] = '3.15.1'
    elif change == 'fake-pypi-python':
        items[0]['purl'] = 'pkg:pypi/python@3.15.2'
    elif change == 'missing-binary-identity':
        items[0]['properties'] = []
    elif change == 'foreign-debian':
        items.append({'name': 'libc6', 'version': '1', 'purl': 'pkg:deb/debian/libc6@1'})
    elif change in ('extra-apk', 'old-python-apk'):
        name = 'python3.15' if change == 'old-python-apk' else 'busybox'
        items.append({'name': name, 'version': '3.15.1', 'purl': f'pkg:apk/wolfi/{name}@3.15.1'})
    elif change == 'wrong-clamav':
        next(item for item in items if item['name'] == 'clamav')['version'] = '1.4.3'
    elif change == 'wrong-wheel':
        next(item for item in items if item['name'] == 'pypdf')['version'] = '6.21.2'
    elif change == 'missing-archive':
        provenance['components'].pop()
    elif change == 'missing-source-bom':
        items.pop()
    elif change == 'changed-source-bom':
        items[-1]['hashes'][0]['content'] = '0' * 64
    elif change == 'unconsumed-provenance':
        items[-2]['properties'] = []
    elif change == 'changed-archive':
        provenance['components'][0]['properties'][0]['value'] = '0' * 64
    elif change == 'missing-file-evidence':
        provenance['components'][0]['properties'].pop()
    elif change == 'empty-raw':
        raw['components'] = []
    else:
        omitted = {'missing-libc': 'glibc-2.44', 'missing-clamav': 'clamav',
                   'missing-wheel': 'cryptography',
                   'missing-archive': lock['clamav']['url'].rsplit('/', 1)[-1]}[change]
        candidate['components'] = [item for item in items if item['name'] != omitted]
    with pytest.raises(AssertionError):
        validate_inventory(candidate, raw, provenance, lock, digest)


@pytest.mark.parametrize(('successful', 'skipped', 'count'),
                         ((False, [], 4), (True, [('case', 'skip')], 4), (True, [], 3)))
def test_ssl_acceptance_rejects_failure_skip_and_unexecuted_test(successful, skipped, count):
    result = SimpleNamespace(testsRun=count, skipped=skipped, wasSuccessful=lambda: successful)
    with patch.object(runtime.unittest.defaultTestLoader, 'loadTestsFromNames'), \
            patch.object(runtime.unittest, 'TextTestRunner') as runner, \
            patch.object(runtime.sys, 'path', []):
        runner.return_value.run.return_value = result
        with pytest.raises(AssertionError):
            runtime.verify_ssl('/fixture')


def test_ssl_acceptance_requires_exact_upstream_tests_and_tls12():
    result = SimpleNamespace(testsRun=4, skipped=[], wasSuccessful=lambda: True)
    with patch.object(runtime.unittest.defaultTestLoader, 'loadTestsFromNames') as loader, \
            patch.object(runtime.unittest, 'TextTestRunner') as runner, \
            patch.object(runtime.sys, 'path', []):
        runner.return_value.run.return_value = result
        runtime.verify_ssl('/fixture')
        loader.assert_called_once_with(runtime.SSL_TESTS)


def test_runtime_fails_immediately_on_host_or_old_interpreter():
    with patch.object(runtime.Path, 'read_text', return_value='{"pythonVersion":"3.15.2"}'), \
            patch.object(runtime.platform, 'python_version', return_value='3.15.1'), \
            pytest.raises(AssertionError):
        runtime.verify_runtime()


@pytest.mark.parametrize('mode', (0o4600, 0o2600))
def test_complete_filesystem_audit_rejects_elevated_payload(tmp_path, mode):
    payload = tmp_path / 'not-executable'
    payload.write_text('test data only')
    payload.chmod(mode)
    with patch.object(runtime.os, 'geteuid', return_value=0), \
            pytest.raises(AssertionError, match='SUID/SGID payload remains'):
        runtime.verify_no_elevated_files(tmp_path)


def test_complete_filesystem_audit_propagates_permission_error(tmp_path):
    failure = PermissionError('Permission denied')
    with patch.object(runtime.os, 'geteuid', return_value=0), \
            patch.object(runtime.os, 'scandir', side_effect=failure), \
            pytest.raises(PermissionError) as captured:
        runtime.verify_no_elevated_files(tmp_path)
    assert captured.value is failure


def test_complete_filesystem_audit_rejects_nonroot_before_scan():
    with patch.object(runtime.os, 'geteuid', return_value=65534), \
            patch.object(runtime.os, 'scandir') as scan, \
            pytest.raises(AssertionError, match='root build context'):
        runtime.verify_no_elevated_files()
    scan.assert_not_called()


def test_complete_filesystem_audit_checks_nested_files_and_not_symlink_targets(tmp_path):
    nested = tmp_path / 'var/lib/private'
    nested.mkdir(parents=True)
    (nested / 'ordinary').write_text('safe')
    (tmp_path / 'cycle').symlink_to(tmp_path, target_is_directory=True)
    with patch.object(runtime.os, 'geteuid', return_value=0):
        runtime.verify_no_elevated_files(tmp_path)


def test_runtime_cli_does_not_repeat_privileged_audit_and_runs_nonroot_ssl():
    with patch.object(runtime.sys, 'argv', ['acceptance', '--runtime-user', '65534',
                                         '--cpython-tests', '/fixtures']), \
            patch.object(runtime.os, 'geteuid', return_value=65534), \
            patch.object(runtime.os, 'getegid', return_value=65534), \
            patch.object(runtime, 'verify_no_elevated_files') as audit, \
            patch.object(runtime, 'verify_runtime', return_value={}) as imports, \
            patch.object(runtime, 'verify_ssl') as ssl_check:
        runtime.main()
    audit.assert_not_called()
    imports.assert_called_once_with()
    ssl_check.assert_called_once_with('/fixtures')


def test_audit_cli_runs_only_complete_audit():
    with patch.object(runtime.sys, 'argv', ['acceptance', '--audit-elevated-files']), \
            patch.object(runtime, 'verify_no_elevated_files') as audit, \
            patch.object(runtime, 'verify_runtime') as imports:
        runtime.main()
    audit.assert_called_once_with()
    imports.assert_not_called()


@pytest.mark.parametrize('uid', (0, 65532))
def test_runtime_cli_rejects_wrong_identity(uid):
    with patch.object(runtime.sys, 'argv', ['acceptance', '--runtime-user', '65534']), \
            patch.object(runtime.os, 'geteuid', return_value=uid), \
            patch.object(runtime.os, 'getegid', return_value=65534), \
            patch.object(runtime, 'verify_runtime') as imports, \
            pytest.raises(AssertionError, match='decoder identity'):
        runtime.main()
    imports.assert_not_called()


@pytest.mark.parametrize('arguments', ([], ['--audit-elevated-files', '--runtime-user', '65534'],
                                      ['--audit-elevated-files', '--cpython-tests', '/fixtures']))
def test_cli_requires_one_explicit_validation_context(arguments):
    with patch.object(runtime.sys, 'argv', ['acceptance', *arguments]), \
            pytest.raises(SystemExit) as failure:
        runtime.main()
    assert failure.value.code == 2


@pytest.mark.parametrize('version', ('TLSv1.2', 'TLSv1.3'))
def test_tls12_acceptance_requires_actual_negotiated_version(version):
    from unittest.mock import MagicMock
    upstream = MagicMock()
    client_context, server_context = SimpleNamespace(), SimpleNamespace()
    upstream.testing_context.return_value = (client_context, server_context, 'fixture')
    upstream.connected_bio_pair.return_value = (SimpleNamespace(version=lambda: version),
                                                SimpleNamespace(version=lambda: version))
    with patch.object(runtime.importlib, 'import_module', return_value=upstream), \
            patch.object(runtime.ssl, 'HAS_TLSv1_2', True):
        case = runtime.TLS12MemoryBIOAcceptance()
        if version != 'TLSv1.2':
            with pytest.raises(AssertionError):
                case.runTest()
        else:
            case.runTest()
    assert client_context.minimum_version == client_context.maximum_version == runtime.ssl.TLSVersion.TLSv1_2
    assert server_context.minimum_version == server_context.maximum_version == runtime.ssl.TLSVersion.TLSv1_2


def test_tls12_acceptance_rejects_false_openssl4_capability_flag():
    with patch.object(runtime.ssl, 'HAS_TLSv1_2', False), pytest.raises(AssertionError):
        runtime.TLS12MemoryBIOAcceptance().runTest()


def test_sbom_cli_accepts_four_documents_and_binds_exact_source_bytes(tmp_path):
    import json
    from pathlib import Path
    import subprocess
    import sys

    candidate, raw, provenance, lock, _ = complete_inventory()
    paths = []
    for name, value in zip(('enriched', 'raw', 'source', 'lock'), (candidate, raw, provenance, lock)):
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(value, sort_keys=True) + '\n')
        paths.append(str(path))
    script = Path(__file__).with_name('media_inspector_sbom_acceptance.py')
    command = [sys.executable, str(script), *paths]
    success = subprocess.run(command, check=True, capture_output=True, text=True, timeout=20)
    assert 'Verified raw inventory preservation' in success.stdout
    # JSON-equivalent but byte-different provenance must not match the image BOM.
    with Path(paths[2]).open('a') as source:
        source.write('\n')
    failure = subprocess.run(command, check=False, capture_output=True, text=True, timeout=20)
    assert failure.returncode != 0
    assert 'Consumed source BOM digest missing/changed' in failure.stderr
