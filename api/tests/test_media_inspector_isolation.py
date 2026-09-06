import base64
import hashlib
import inspect
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from api.services import media_inspector_service as service
from api.services.media_inspector_client import MediaInspectorClientError, inspect_media_via_spool
from api.services.media_inspector_receipt import InspectorReceiptError, sign_receipt, verify_receipt

NOW = datetime(2026, 9, 7, 0, 0, tzinfo=UTC)
SIGNING_KEY = Ed25519PrivateKey.from_private_bytes(b'k' * 32)
VERIFY_KEY = SIGNING_KEY.public_key()
DIGEST = 'a' * 64
BUILD_IDENTITY = 'base2-media-inspector:' + 'b' * 64


def payload(**changes):
    value = {
        'schemaVersion': 'base2-media-inspection-v1',
        'jobId': 'job-1',
        'nonce': 'nonce-1',
        'assetId': '00000000-0000-0000-0000-000000000110',
        'objectVersion': 1,
        'sourceSha256': DIGEST,
        'requestedMediaType': 'image/png',
        'observedMediaType': 'image/png',
        'decision': 'accepted',
        'scanner': {
            'engine': 'clamav',
            'version': '1.4.3',
            'definitionsVersion': '27788',
            'definitionsAt': '2026-09-06T23:00:00Z',
            'verdict': 'clean',
        },
        'decoder': {
            'name': 'pillow',
            'version': '12.3.0',
            'buildIdentity': BUILD_IDENTITY,
        },
        'measurements': {'pixels': 1},
        'preview': {
            'mediaType': 'image/png',
            'sha256': hashlib.sha256(b'p').hexdigest(),
            'byteSize': 1,
            'width': 1,
            'height': 1,
        },
        'startedAt': '2026-09-06T23:59:59Z',
        'finishedAt': '2026-09-07T00:00:00Z',
    }
    value.update(changes)
    return value


def verify(receipt, **changes):
    values = {
        'key': VERIFY_KEY,
        'expected_job_id': 'job-1',
        'expected_nonce': 'nonce-1',
        'expected_asset_id': '00000000-0000-0000-0000-000000000110',
        'expected_object_version': 1,
        'expected_source_sha256': DIGEST,
        'expected_media_type': 'image/png',
        'now': NOW,
    }
    values.update(changes)
    return verify_receipt(receipt, **values)


def test_receipt_is_authenticated_and_binds_every_promotion_identity():
    receipt = sign_receipt(payload(), SIGNING_KEY)
    assert verify(receipt)['decoder']['version'] == '12.3.0'
    for mutation in (
        lambda r: r['payload']['preview'].update({'byteSize': 2}),
        lambda r: r['payload'].update({'assetId': 'other'}),
        lambda r: r.update({'signature': '0' * 64}),
    ):
        changed = json.loads(json.dumps(receipt))
        mutation(changed)
        with pytest.raises(InspectorReceiptError):
            verify(changed)


def test_stale_cross_nonce_and_scanner_evidence_fail_closed():
    receipt = sign_receipt(payload(), SIGNING_KEY)
    with pytest.raises(InspectorReceiptError, match='binding_invalid'):
        verify(receipt, expected_nonce='new-attempt')
    with pytest.raises(InspectorReceiptError, match='receipt_stale'):
        verify(receipt, now=NOW + timedelta(minutes=3))
    old = payload()
    old['scanner']['definitionsAt'] = '2026-09-05T00:00:00Z'
    with pytest.raises(InspectorReceiptError, match='scanner_stale'):
        verify(sign_receipt(old, SIGNING_KEY))


def request(content=b'source'):
    return {
        'schemaVersion': 'base2-media-inspection-request-v1',
        'jobId': 'job-1',
        'nonce': 'nonce-1',
        'assetId': '00000000-0000-0000-0000-000000000110',
        'objectVersion': 1,
        'sourceSha256': hashlib.sha256(content).hexdigest(),
        'mediaType': 'image/png',
    }


def test_supervisor_binds_stable_scanner_and_decoder_evidence():
    content = b'source'
    preview = b'p'
    health = {
        'engine': 'clamav',
        'version': '1.4.3',
        'definitionsVersion': '27788',
        'definitionsAt': '2026-09-06T23:00:00Z',
    }
    decoded = {
        'decoderName': 'pillow',
        'decoderVersion': '12.3.0',
        'observedMediaType': 'image/png',
        'measurements': {'pixels': 1},
        'preview': {
            'mediaType': 'image/png',
            'sha256': hashlib.sha256(preview).hexdigest(),
            'byteSize': 1,
            'width': 1,
            'height': 1,
        },
        'previewBase64': base64.b64encode(preview).decode(),
    }
    receipt, result = service.inspect_request(
        request(content),
        content,
        key=SIGNING_KEY,
        build_identity=BUILD_IDENTITY,
        now=lambda: NOW,
        health_reader=lambda: health,
        scanner=lambda _: 'clean',
        decoder=lambda *_: decoded,
    )
    assert (
        result == preview
        and verify(receipt, expected_source_sha256=hashlib.sha256(content).hexdigest())['scanner'][
            'verdict'
        ]
        == 'clean'
    )


def test_scanner_change_crash_oom_and_timeout_never_produce_receipt(monkeypatch):
    content = b'source'
    calls = iter(
        [
            {
                'engine': 'clamav',
                'version': '1',
                'definitionsVersion': '1',
                'definitionsAt': '2026-09-06T23:00:00Z',
            },
            {
                'engine': 'clamav',
                'version': '1',
                'definitionsVersion': '2',
                'definitionsAt': '2026-09-06T23:00:00Z',
            },
        ]
    )
    with pytest.raises(service.MediaInspectorServiceError, match='identity_changed'):
        service.inspect_request(
            request(content),
            content,
            key=SIGNING_KEY,
            build_identity=BUILD_IDENTITY,
            now=lambda: NOW,
            health_reader=lambda: next(calls),
            scanner=lambda _: 'clean',
            decoder=lambda *_: {},
        )
    for outcome in (
        subprocess.CompletedProcess([], 66, b'', b'crash'),
        subprocess.CompletedProcess([], -9, b'', b''),
    ):
        with pytest.raises(service.MediaInspectorServiceError, match='decoder_failed'):
            service._decode(content, 'image/png', run=lambda *a, result=outcome, **k: result)

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)

    monkeypatch.setattr(service.subprocess, 'run', timed_out)
    with pytest.raises(service.MediaInspectorServiceError, match='dependency_unavailable'):
        service._fixed_run(['/fixed'], content=content, timeout=1)


def test_every_hostile_parser_runs_as_distinct_keyless_identity(monkeypatch):
    captured = {}

    def completed(argv, **kwargs):
        captured.update(argv=argv, kwargs=kwargs)
        kwargs['stdout'].write(b'ok')
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(service.subprocess, 'run', completed)
    result = service._fixed_run(['/usr/bin/example'], content=b'hostile')
    assert result.returncode == 0
    assert captured['argv'][:3] == ['/usr/bin/setpriv', '--reuid=65534', '--regid=65534']
    assert '--bounding-set=-all' in captured['argv']
    assert 'MEDIA_INSPECTOR_SIGNING_KEY' not in captured['kwargs']['env']
    assert captured['kwargs']['cwd'] == '/tmp' and captured['kwargs']['close_fds'] is True


def test_missing_attestation_or_inspector_times_out_without_success(tmp_path):
    content = b'source'
    with pytest.raises(MediaInspectorClientError, match='attestation_unavailable'):
        inspect_media_via_spool(
            content=content,
            expected_sha256=hashlib.sha256(content).hexdigest(),
            media_type='image/png',
            asset_id=__import__('uuid').UUID(int=110),
            object_version=1,
            observed_at=NOW,
            spool_root=str(tmp_path),
            encoded_verify_key='',
            timeout_seconds=1,
        )


def test_main_worker_has_no_decoder_import_and_manifests_isolate_service():
    from api.services import media_library_runtime

    source = inspect.getsource(media_library_runtime).split('def inspect_media_payload', 1)[0]
    assert 'media_library_parser' not in source and 'media_library_processor' not in source
    root = Path(__file__).resolve().parents[2]
    for name in ('local.docker.yml', 'development.docker.yml'):
        manifest = yaml.safe_load((root / name).read_text())
        inspector = manifest['services']['media-inspector']
        assert inspector['network_mode'] == 'none' and inspector['read_only'] is True
        assert inspector['pid'] == 'private' and inspector['ipc'] == 'private'
        assert (
            inspector['cap_drop'] == ['ALL']
            and inspector['cap_add'] == ['SETUID', 'SETGID', 'SETPCAP']
            and inspector['pids_limit'] == 16
        )
        env = '\n'.join(inspector['environment'])
        assert all(
            secret not in env
            for secret in (
                'DB_PASSWORD',
                'TOKEN_PEPPER',
                'IDENTITY_ENCRYPTION_KEY',
                'REDIS_PASSWORD',
            )
        )
        worker = manifest['services']['celery-worker']
        assert 'media_inspector_spool:/var/lib/base2/media-inspector' in worker['volumes']
        worker_env = '\n'.join(worker['environment'])
        assert 'MEDIA_INSPECTOR_VERIFY_KEY=' in worker_env
        assert 'MEDIA_INSPECTOR_SIGNING_KEY' not in worker_env
        assert 'MEDIA_INSPECTOR_SIGNING_KEY=' in env
        assert 'MEDIA_INSPECTOR_VERIFY_KEY' not in env


def test_inspector_image_ships_fixed_scanner_and_ffprobe():
    dockerfile = (Path(__file__).resolve().parents[1] / 'Dockerfile.media-inspector').read_text()
    assert 'clamav ffmpeg' in dockerfile and 'USER inspector' in dockerfile
