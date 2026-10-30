"""Reject a deceptively clean SBOM which omits the real runtime inventory."""
from __future__ import annotations

import json
from pathlib import Path
import sys


def validate_inventory(sbom: dict) -> None:
    components = sbom.get('components', [])
    interpreters = [item for item in components
                    if item.get('name', '').lower() in ('python', 'python3', 'python3.15', 'cpython')
                    and not item.get('purl', '').startswith('pkg:pypi/')]
    assert interpreters, 'SBOM omits the CPython interpreter'
    for item in interpreters:
        assert item.get('version') == '3.15.2', f'Unexpected interpreter inventory: {item.get("version")}'
        properties = {entry['name']: entry['value'] for entry in item.get('properties', [])}
        assert properties.get('syft:package:type') == 'binary', 'CPython must be identified from its binary'
    assert not any(item.get('purl', '').startswith('pkg:apk/') for item in components), 'Old Wolfi inventory remains'
    for name in ('libc6', 'libssl3t64', 'libcap-ng0', 'util-linux', 'clamav'):
        matches = [item for item in components if item.get('name') == name
                   and item.get('purl', '').startswith('pkg:deb/')]
        assert matches, f'SBOM omits Debian/scanner package: {name}'
        if name == 'clamav':
            assert all(item.get('version') == '1.5.4-1' for item in matches)
    for name in ('cffi', 'cryptography', 'pillow', 'pycparser', 'pypdf'):
        assert any(item.get('name', '').lower() == name
                   and item.get('purl', '').startswith('pkg:pypi/') for item in components), f'SBOM omits wheel: {name}'


if __name__ == '__main__':
    validate_inventory(json.loads(Path(sys.argv[1]).read_text()))
    print('Verified CPython 3.15.2, Debian, ClamAV and locked wheel inventory')
