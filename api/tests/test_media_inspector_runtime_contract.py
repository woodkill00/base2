"""Negative/positive coverage for fail-closed runtime/SBOM acceptance checks."""
from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from api.tests import media_inspector_runtime_acceptance as runtime
from api.tests.media_inspector_sbom_acceptance import validate_inventory


def complete_inventory():
    components = [{
        'name': 'python', 'version': '3.15.2',
        'properties': [{'name': 'syft:package:type', 'value': 'binary'}],
    }]
    for name in ('libc6', 'libssl3t64', 'libcap-ng0', 'util-linux', 'clamav'):
        components.append({'name': name, 'version': '1.5.4-1' if name == 'clamav' else '1',
                           'purl': f'pkg:deb/debian/{name}@1'})
    for name in ('cffi', 'cryptography', 'pillow', 'pycparser', 'pypdf'):
        components.append({'name': name, 'purl': f'pkg:pypi/{name}@1'})
    return {'components': components}


def test_sbom_accepts_real_fixed_binary_and_complete_inventory():
    validate_inventory(complete_inventory())


@pytest.mark.parametrize('change', ('missing-python', 'old-python', 'fake-pypi-python',
                                  'missing-binary-identity', 'wolfi', 'missing-libc',
                                  'missing-clamav', 'wrong-clamav', 'missing-wheel'))
def test_sbom_rejects_incomplete_or_misleading_inventory(change):
    candidate = copy.deepcopy(complete_inventory())
    items = candidate['components']
    if change == 'missing-python':
        items.pop(0)
    elif change == 'old-python':
        items[0]['version'] = '3.15.1'
    elif change == 'fake-pypi-python':
        items[0]['purl'] = 'pkg:pypi/python@3.15.2'
    elif change == 'missing-binary-identity':
        items[0]['properties'] = []
    elif change == 'wolfi':
        items.append({'name': 'wolfi-baselayout', 'version': '20261024-r1',
                      'purl': 'pkg:apk/wolfi/wolfi-baselayout@20261024-r1'})
    elif change == 'wrong-clamav':
        next(item for item in items if item['name'] == 'clamav')['version'] = '1.4.3'
    else:
        omitted = {'missing-libc': 'libc6', 'missing-clamav': 'clamav',
                   'missing-wheel': 'cryptography'}[change]
        candidate['components'] = [item for item in items if item['name'] != omitted]
    with pytest.raises(AssertionError):
        validate_inventory(candidate)


@pytest.mark.parametrize(('successful', 'skipped', 'count'),
                         ((False, [], 2), (True, [('case', 'skip')], 2), (True, [], 1)))
def test_ssl_acceptance_rejects_failure_skip_and_unexecuted_test(successful, skipped, count):
    result = SimpleNamespace(testsRun=count, skipped=skipped, wasSuccessful=lambda: successful)
    with patch.object(runtime.unittest.defaultTestLoader, 'loadTestsFromNames'), \
            patch.object(runtime.unittest, 'TextTestRunner') as runner, \
            patch.object(runtime.sys, 'path', []):
        runner.return_value.run.return_value = result
        with pytest.raises(AssertionError):
            runtime.verify_ssl('/fixture')


def test_ssl_acceptance_requires_exact_two_upstream_tests():
    result = SimpleNamespace(testsRun=2, skipped=[], wasSuccessful=lambda: True)
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
