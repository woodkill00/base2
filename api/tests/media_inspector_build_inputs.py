"""Build-only verified inputs and source-derived scanner SBOM (never an installer)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request


PROVENANCE = 'usr/local/share/base2/clamav'
SCANNER_FILES = {
    '/usr/bin/clamscan': 'usr/local/bin/clamscan',
    '/usr/local/lib/libclamav.so.12.1.0': 'usr/local/lib/libclamav.so.12.1.0',
    '/usr/local/lib/libclamav.so.12': 'usr/local/lib/libclamav.so.12',
    '/usr/local/lib/libclammspack.so.0.8.0': 'usr/local/lib/libclammspack.so.0.8.0',
    '/usr/local/lib/libclammspack.so.0': 'usr/local/lib/libclammspack.so.0',
    '/usr/local/etc/certs/clamav.crt': 'usr/local/etc/certs/clamav.crt',
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download_verified(url: str, digest: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'Input digest mismatch: {destination.name}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)


def prepare(lock: dict, destination: Path) -> None:
    repository = destination / 'repository/x86_64'
    repository.mkdir(parents=True, exist_ok=True)
    index = repository / 'APKINDEX.tar.gz'
    # The index is signed, refreshable trust metadata, not a version resolver.
    # Native apk verifies its signature BEFORE installing anything. Exact package
    # versions/control digests/full-file hashes and the entire closure are locked.
    with urllib.request.urlopen(lock['repository']['indexUrl'], timeout=120) as response:
        index.write_bytes(response.read())
    with tarfile.open(index) as archive:
        index_file = archive.extractfile('APKINDEX')
        if index_file is None:
            raise ValueError('Repository index missing APKINDEX')
        entries = {}
        for stanza in index_file.read().decode().split('\n\n'):
            fields = dict(line.split(':', 1) for line in stanza.splitlines() if ':' in line)
            if 'P' in fields:
                entries[fields['P'], fields['V']] = fields
    for package in lock['apks']:
        indexed = entries.get((package['name'], package['version']), {})
        if indexed.get('C') != package['indexChecksum']:
            raise ValueError(f'Locked package absent/changed in signed index: {package["name"]}')
        download_verified(package['url'], package['sha256'], repository / package['filename'])
    (destination / 'key.sha256').write_text(lock['repository']['keySha256'] + '  /locked-keys/wolfi-signing.rsa.pub\n')
    for role in ('build', 'runtime'):
        pins = [f'{item["name"]}={item["version"]}' for item in lock['apks'] if role in item['roles']]
        (destination / f'{role}-pins.txt').write_text('\n'.join(pins) + '\n')
    for item in lock['patches']:
        download_verified(item['url'], item['sha256'], destination / 'patches' / item['filename'])
    (destination / 'repository-evidence.json').write_text(json.dumps({
        'indexUrl': lock['repository']['indexUrl'], 'indexSha256': sha256(index),
        'keySha256': lock['repository']['keySha256'],
        'packageCount': len(lock['apks']),
        'trust': 'native apk verifies signed index; immutable package hashes and control digests',
    }, sort_keys=True) + '\n')


def record_scanner_files(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'control').write_bytes((source / 'control').read_bytes())
    (destination / 'files.json').write_text(json.dumps({
        installed: sha256(source / original) for installed, original in SCANNER_FILES.items()
    }, sort_keys=True) + '\n')


def scanner_bom(lock: dict, *, root: Path = Path('/')) -> dict:
    expected = lock['clamav']
    provenance = root / PROVENANCE
    control = (provenance / 'control').read_text()
    if 'Package: clamav\n' not in control or f'Version: {expected["packageVersion"]}\n' not in control:
        raise ValueError('Imported ClamAV control version mismatch')
    files = json.loads((provenance / 'files.json').read_text())
    if set(files) != set(SCANNER_FILES):
        raise ValueError('ClamAV owned-file evidence missing')
    for name, digest in files.items():
        if sha256(root / name.lstrip('/')) != digest:
            raise ValueError(f'ClamAV file digest mismatch: {name}')
    output = subprocess.check_output([str(root / 'usr/bin/clamscan'), '--version'], timeout=20).decode()
    match = re.match(r'ClamAV ([0-9]+\.[0-9]+\.[0-9]+)(?:/|\s|$)', output)
    if match is None or match[1] != expected['version']:
        raise ValueError('Executed ClamAV upstream version mismatch')
    version = match[1]
    properties = [
        {'name': 'base2:source:controlSha256', 'value': sha256(provenance / 'control')},
        {'name': 'base2:source:archiveSha256', 'value': expected['sha256']},
        {'name': 'base2:source:packageVersion', 'value': expected['packageVersion']},
        *({'name': f'base2:file:sha256:{name}', 'value': digest} for name, digest in sorted(files.items())),
    ]
    upstream = {
        'type': 'application', 'bom-ref': f'pkg:generic/clamav@{version}',
        'name': 'clamav', 'version': version, 'purl': f'pkg:generic/clamav@{version}',
        'cpe': f'cpe:2.3:a:clamav:clamav:{version}:*:*:*:*:*:*:*',
        'supplier': {'name': 'Cisco Talos'}, 'properties': properties,
        'externalReferences': [{'type': 'distribution', 'url': expected['url'],
                                'hashes': [{'alg': 'SHA-256', 'content': expected['sha256']}]}],
    }
    imported = {
        'type': 'file', 'bom-ref': 'urn:sha256:' + expected['sha256'],
        'name': expected['url'].rsplit('/', 1)[-1], 'version': expected['packageVersion'],
        'hashes': [{'alg': 'SHA-256', 'content': expected['sha256']}],
        'description': 'Original upstream Cisco package, not a Debian-maintained OS package',
    }
    return {'bomFormat': 'CycloneDX', 'specVersion': '1.6', 'version': 1,
            'components': [upstream, imported],
            'dependencies': [{'ref': upstream['bom-ref'], 'dependsOn': [imported['bom-ref']]}]}


def record_python_files(lock: dict, root: Path, destination: Path) -> None:
    files = {str(path.relative_to(root)): sha256(path)
             for path in sorted(root.rglob('*')) if path.is_file()}
    if 'usr/local/bin/python3.15' not in files:
        raise ValueError('Compiled interpreter payload missing')
    destination.write_text(json.dumps({
        'name': 'CPython', 'version': lock['pythonVersion'],
        'source': lock['source'], 'patches': lock['patches'],
        'buildRecipe': 'api/Dockerfile.media-inspector', 'files': files,
    }, sort_keys=True) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'scanner-files', 'scanner-bom', 'python-files'))
    parser.add_argument('--lock', default='/usr/local/share/base2/media-inspector-runtime.lock.json')
    parser.add_argument('--destination', required=True)
    parser.add_argument('--source')
    args = parser.parse_args()
    destination = Path(args.destination)
    if args.mode == 'scanner-files':
        record_scanner_files(Path(args.source), destination)
    else:
        lock = json.loads(Path(args.lock).read_text())
        if args.mode == 'prepare':
            prepare(lock, destination)
        elif args.mode == 'python-files':
            record_python_files(lock, Path(args.source), destination)
        else:
            destination.write_text(json.dumps(scanner_bom(lock), sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
