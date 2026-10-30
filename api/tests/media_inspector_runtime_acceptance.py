"""Build/CI acceptance against the actual final interpreter, never a host proxy."""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import ssl
import subprocess
import sys
import unittest


SSL_TESTS = (
    'test.test_ssl.SSLObjectTests.test_distrusted_spki',
    'test.test_ssl.SSLObjectTests.test_unwrap',
)


def verify_no_elevated_files() -> None:
    # Immutable-image audit needs a root build context with DAC traversal rights.
    # Never ignore permission errors: incomplete inventory must fail the build.
    assert os.geteuid() == 0, 'Full filesystem audit requires the root build context'
    elevated = subprocess.check_output(
        ['/usr/bin/find', '/', '-xdev', '-type', 'f', '-perm', '/6000', '-print'],
        timeout=20,
    )
    assert not elevated.strip(), f'SUID/SGID payload remains: {elevated!r}'


def verify_runtime() -> dict[str, str]:
    lock = json.loads(Path('/usr/local/share/base2/media-inspector-runtime.lock.json').read_text())
    assert platform.python_version() == lock['pythonVersion'] == '3.15.2'
    assert platform.machine() == 'x86_64'
    assert Path(sys.executable).resolve() == Path('/usr/local/bin/python3.15').resolve()
    assert Path('/usr/bin/python').resolve() == Path(sys.executable).resolve()
    assert not Path('/lib/apk/db/installed').exists(), 'Old Wolfi package database remains'
    assert importlib.util.find_spec('pip') is None, 'Production must not ship pip'
    assert importlib.util.find_spec('ensurepip') is None, 'Production must not bootstrap pip'
    assert not list(Path('/usr/local').rglob('pip-*.whl')), 'Bundled pip wheel remains'
    assert not list(Path('/usr/local/bin').glob('pip*')), 'Pip executable remains'
    assert not Path('/usr/local/lib/python3.15/test').exists(), 'Upstream fixtures leaked'
    status = Path('/var/lib/dpkg/status').read_text()
    for package in ('libc6', 'libssl3t64', 'libcap-ng0', 'util-linux', 'clamav'):
        assert f'Package: {package}\n' in status, f'Missing real inventory: {package}'
    # Import native extension modules, not just each package's pure-Python facade.
    for module in ('_ssl', '_hashlib', '_ctypes', '_cffi_backend', 'PIL._imaging',
                   'cryptography.hazmat.bindings._rust', 'pycparser', 'pypdf'):
        importlib.import_module(module)
    expected = {'cffi': '2.1.1', 'cryptography': '50.0.1', 'pillow': '13.0.0',
                'pycparser': '3.0', 'pypdf': '6.21.2'}
    for package, version in expected.items():
        assert importlib.metadata.version(package) == version
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from PIL import Image
    from pypdf import PdfReader, PdfWriter

    signing_key = Ed25519PrivateKey.generate()
    message = b'base2 media runtime ABI acceptance'
    signing_key.public_key().verify(signing_key.sign(message), message)
    png = io.BytesIO()
    Image.new('RGB', (2, 2), 'red').save(png, format='PNG')
    png.seek(0)
    with Image.open(png) as decoded:
        decoded.load()
        assert decoded.size == (2, 2)
    pdf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(pdf)
    pdf.seek(0)
    assert len(PdfReader(pdf).pages) == 1
    for binary in ('setpriv', 'clamscan', 'ffmpeg', 'ffprobe'):
        option = '--version' if binary in ('setpriv', 'clamscan') else '-version'
        subprocess.run([f'/usr/bin/{binary}', option], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    return {'python': platform.python_version(), 'openssl': ssl.OPENSSL_VERSION,
            'executable': str(Path(sys.executable).resolve())}


def verify_ssl(cpython_tests: str) -> None:
    # Only the upstream test package is mounted: stdlib and _ssl stay native to
    # the final slim runtime. The compromised-chain regression requires code 28.
    sys.path.insert(0, cpython_tests)
    suite = unittest.defaultTestLoader.loadTestsFromNames(SSL_TESTS)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.testsRun == len(SSL_TESTS)
    assert result.wasSuccessful() and not result.skipped, 'SSL regression did not pass completely'


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--audit-elevated-files', action='store_true')
    mode.add_argument('--runtime-user', type=int, choices=(65534,))
    parser.add_argument('--cpython-tests')
    args = parser.parse_args()
    if args.audit_elevated_files:
        if args.cpython_tests:
            parser.error('SSL checks require the nonroot runtime context')
        verify_no_elevated_files()
        print('Verified complete immutable-image SUID/SGID audit')
        return
    assert os.geteuid() == os.getegid() == args.runtime_user, 'Expected nonroot decoder identity'
    identity = verify_runtime()
    identity.update(uid=str(os.geteuid()), gid=str(os.getegid()))
    if args.cpython_tests:
        verify_ssl(args.cpython_tests)
    print(json.dumps(identity, sort_keys=True))


if __name__ == '__main__':
    main()
