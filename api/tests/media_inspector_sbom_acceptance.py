"""Reject omitted inventory or supplemental identity not consumed by Syft."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


WHEELS = {'cffi': '2.1.1', 'cryptography': '50.0.1', 'pillow': '13.0.0',
          'pycparser': '3.0', 'pypdf': '6.21.4'}


def identity(item: dict) -> tuple[str, str, str, str]:
    properties = {entry['name']: entry['value'] for entry in item.get('properties', [])}
    return (item.get('name', ''), item.get('version', ''), item.get('purl', ''),
            properties.get('syft:package:type', ''))


def validate_inventory(sbom: dict, raw: dict, provenance: dict, lock: dict, provenance_sha256: str) -> None:
    components = sbom.get('components', [])
    # IDs/tool metadata can differ between separate cataloger executions. Every
    # original package identity, including duplicate occurrences, must survive.
    assert raw.get('components'), 'Raw inventory is empty'
    missing = Counter(map(identity, raw['components'])) - Counter(map(identity, components))
    assert not missing, f'Additive SBOM removed raw inventory: {missing}'
    interpreters = [item for item in components
                    if item.get('name', '').lower() in ('python', 'python3', 'python3.15', 'cpython')
                    and not item.get('purl', '').startswith('pkg:pypi/')]
    assert interpreters, 'SBOM omits the CPython interpreter'
    for item in interpreters:
        assert item.get('version') == lock['pythonVersion'] == '3.15.2', 'Unexpected interpreter version'
        assert identity(item)[3] == 'binary', 'CPython must be identified from its binary'
    assert not any(item.get('purl', '').startswith('pkg:deb/') for item in components), 'Foreign OS package identity'
    native = [item for item in components if item.get('purl', '').startswith('pkg:apk/')]
    expected = {(item['name'], item['version']) for item in lock['apks'] if 'runtime' in item['roles']}
    assert {(item['name'], item['version']) for item in native} == expected, 'APK closure differs from lock'
    assert not any(item['name'].startswith('python') for item in native), 'Vendor Python APK remains'
    for name, version in WHEELS.items():
        matches = [item for item in components if item.get('name', '').lower() == name
                   and item.get('purl', '').startswith('pkg:pypi/')]
        assert matches and all(item.get('version') == version for item in matches), f'SBOM omits/changes wheel: {name}'
    scanner = lock['clamav']
    purl = f'pkg:generic/clamav@{scanner["version"]}'
    expected_cpe = f'cpe:2.3:a:clamav:clamav:{scanner["version"]}:*:*:*:*:*:*:*'
    imported = [item for item in provenance.get('components', []) if item.get('purl') == purl]
    assert len(imported) == 1 and imported[0].get('cpe') == expected_cpe, 'Scanner provenance identity missing'
    properties = {item['name']: item['value'] for item in imported[0].get('properties', [])}
    assert properties.get('base2:source:archiveSha256') == scanner['sha256'], 'Scanner archive hash differs'
    assert properties.get('base2:source:packageVersion') == scanner['packageVersion'], 'Scanner vendor revision differs'
    assert len(properties.get('base2:source:controlSha256', '')) == 64, 'Original control digest missing'
    for path in ('/usr/bin/clamscan', '/usr/local/lib/libclamav.so.12.1.0',
                 '/usr/local/lib/libclamav.so.12', '/usr/local/lib/libclammspack.so.0.8.0',
                 '/usr/local/lib/libclammspack.so.0', '/usr/local/etc/certs/clamav.crt'):
        assert len(properties.get(f'base2:file:sha256:{path}', '')) == 64, f'Scanner file evidence missing: {path}'
    source_path = '/usr/local/share/base2/clamav.bom.json'
    consumed = [item for item in components if item.get('purl') == purl
                and item.get('version') == scanner['version'] and item.get('cpe') == expected_cpe]
    assert consumed, 'Syft did not consume upstream scanner identity'
    for item in consumed:
        found = {entry['name']: entry['value'] for entry in item.get('properties', [])}
        assert found.get('syft:package:foundBy') == 'sbom-cataloger', 'Unbound scanner identity'
        assert source_path in [value for name, value in found.items()
                               if name.startswith('syft:location:') and name.endswith(':path')], 'Scanner source location missing'
    assert any(item.get('type') == 'file' and item.get('name') == source_path
               and {'alg': 'SHA-256', 'content': provenance_sha256} in item.get('hashes', [])
               for item in components), 'Consumed source BOM digest missing/changed'
    # The upstream .deb is a source artifact, not an installed package. Syft
    # retains its containing BOM's file hash, not that uninstalled archive as a
    # software package. Verify the original record in the bound source document.
    archive_name = scanner['url'].rsplit('/', 1)[-1]
    assert any(item.get('name') == archive_name and item.get('version') == scanner['packageVersion']
               and {'alg': 'SHA-256', 'content': scanner['sha256']} in item.get('hashes', [])
               for item in provenance['components']), 'Original scanner artifact missing'


if __name__ == '__main__':
    payloads = [Path(path).read_bytes() for path in sys.argv[1:]]
    assert len(payloads) == 4, 'Expected enriched SBOM, raw SBOM, source BOM and runtime lock'
    validate_inventory(*(json.loads(data) for data in payloads), hashlib.sha256(payloads[2]).hexdigest())
    print('Verified raw inventory preservation, CPython 3.15.2, native APK closure, upstream ClamAV and locked wheels')
