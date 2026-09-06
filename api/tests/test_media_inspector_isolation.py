import base64
import hashlib
import io
import inspect
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from api.services import media_inspector_client as client
from api.services import media_inspector_runner as runner
from api.services import media_inspector_service as service
from api.services.media_inspector_client import MediaInspectorClientError, inspect_media_via_spool
from api.services.media_inspector_receipt import (
    InspectorReceiptError,
    load_signing_key,
    load_verify_key,
    sign_receipt,
    verify_receipt,
)

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


def test_spool_client_accepts_only_bound_signed_result(monkeypatch, tmp_path):
    content = b'source'
    preview = b'preview'
    encoded_verify_key = base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode()
    handled = False

    def complete_job(_delay):
        nonlocal handled
        if handled:
            return
        job = next(path for path in tmp_path.iterdir() if path.is_dir())
        request_value = json.loads((job / 'request.json').read_text())
        finished = datetime.now(UTC)
        receipt_payload = payload(
            jobId=request_value['jobId'],
            nonce=request_value['nonce'],
            assetId=request_value['assetId'],
            objectVersion=request_value['objectVersion'],
            sourceSha256=request_value['sourceSha256'],
            requestedMediaType=request_value['mediaType'],
            finishedAt=finished.isoformat().replace('+00:00', 'Z'),
            startedAt=(finished - timedelta(seconds=1)).isoformat().replace('+00:00', 'Z'),
        )
        receipt_payload['scanner']['definitionsAt'] = (
            (finished - timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
        )
        receipt_payload['preview'].update(
            sha256=hashlib.sha256(preview).hexdigest(), byteSize=len(preview)
        )
        (job / 'preview.bin').write_bytes(preview)
        (job / 'receipt.json').write_text(json.dumps(sign_receipt(receipt_payload, SIGNING_KEY)))
        (job / 'complete').write_bytes(b'1')
        handled = True

    monkeypatch.setattr(client.time, 'sleep', complete_job)
    result = inspect_media_via_spool(
        content=content,
        expected_sha256=hashlib.sha256(content).hexdigest(),
        media_type='image/png',
        asset_id=UUID(int=110),
        object_version=1,
        observed_at=NOW,
        spool_root=str(tmp_path),
        encoded_verify_key=encoded_verify_key,
        timeout_seconds=1,
    )
    assert result.preview.content == preview
    assert result.preview.sha256 == hashlib.sha256(preview).hexdigest()
    assert result.scanner_ref == 'clamav:1.4.3-27788'
    assert result.decoder_ref == 'pillow:12.3.0'
    assert result.measurements == {'pixels': 1}
    assert not list(tmp_path.iterdir())


def test_spool_client_rejection_timeout_and_request_guards(monkeypatch, tmp_path):
    content = b'source'
    encoded_verify_key = base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode()
    common = {
        'content': content,
        'expected_sha256': hashlib.sha256(content).hexdigest(),
        'media_type': 'image/png',
        'asset_id': UUID(int=110),
        'object_version': 1,
        'observed_at': NOW,
        'spool_root': str(tmp_path),
        'encoded_verify_key': encoded_verify_key,
        'timeout_seconds': 1,
    }
    for changes, error in (
        ({'content': b'', 'expected_sha256': hashlib.sha256(b'').hexdigest()}, 'integrity_failed'),
        ({'expected_sha256': '0' * 64}, 'integrity_failed'),
        ({'object_version': True}, 'request_invalid'),
        ({'timeout_seconds': 0}, 'request_invalid'),
        ({'spool_root': 'relative'}, 'isolation_unavailable'),
    ):
        with pytest.raises(MediaInspectorClientError, match=error):
            inspect_media_via_spool(**(common | changes))

    def reject(_delay):
        job = next(path for path in tmp_path.iterdir() if path.is_dir())
        (job / 'failed').write_bytes(b'rejected')

    monkeypatch.setattr(client.time, 'sleep', reject)
    with pytest.raises(MediaInspectorClientError, match='rejected'):
        inspect_media_via_spool(**common)
    assert not list(tmp_path.iterdir())

    ticks = iter((0.0, 2.0))
    monkeypatch.setattr(client.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(client.time, 'sleep', lambda _delay: None)
    with pytest.raises(MediaInspectorClientError, match='timeout'):
        inspect_media_via_spool(**common)


def test_receipt_schema_rejects_malformed_nested_evidence():
    mutations = (
        lambda value: value.update(schemaVersion='wrong'),
        lambda value: value.update(jobId=''),
        lambda value: value.update(objectVersion=True),
        lambda value: value.update(sourceSha256='bad'),
        lambda value: value.update(scanner=[]),
        lambda value: value['scanner'].update(verdict='infected'),
        lambda value: value['scanner'].update(engine='bad ref!'),
        lambda value: value['scanner'].update(definitionsAt='not-a-time'),
        lambda value: value.update(decoder=[]),
        lambda value: value['decoder'].update(buildIdentity='operator-claim'),
        lambda value: value.update(measurements={'unknown': 1}),
        lambda value: value.update(measurements={'pixels': True}),
        lambda value: value.update(preview=[]),
        lambda value: value['preview'].update(byteSize=0),
        lambda value: value['preview'].update(width=True),
        lambda value: value.update(startedAt='bad'),
    )
    for mutate in mutations:
        candidate = payload()
        mutate(candidate)
        with pytest.raises(InspectorReceiptError, match='receipt_invalid'):
            sign_receipt(candidate, SIGNING_KEY)


def test_receipt_key_and_outer_envelope_guards():
    encoded_private = base64.urlsafe_b64encode(b'k' * 32).decode()
    encoded_public = base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode()
    assert load_signing_key(encoded_private)
    assert load_verify_key(encoded_public)
    for encoded in ('', '!!!', '£'):
        with pytest.raises(InspectorReceiptError, match='attestation_unavailable'):
            load_verify_key(encoded)
    with pytest.raises(InspectorReceiptError, match='receipt_invalid'):
        verify({'payload': payload()}, expected_job_id='job-1')
    receipt = sign_receipt(payload(), SIGNING_KEY)
    receipt['resultSha256'] = '0' * 64
    with pytest.raises(InspectorReceiptError, match='receipt_invalid'):
        verify(receipt)


def test_runner_decodes_image_pdf_and_stream_metadata(monkeypatch):
    preview = SimpleNamespace(
        content=b'p',
        media_type='image/png',
        sha256=hashlib.sha256(b'p').hexdigest(),
        width=3,
        height=2,
    )
    monkeypatch.setattr(runner, 'generate_media_preview', lambda **_kwargs: preview)
    monkeypatch.setattr(runner.importlib.metadata, 'version', lambda name: f'{name}-version')
    image = runner.decode(b'image', 'image/png')
    assert image['decoderName'] == 'pillow' and image['measurements'] == {'pixels': 6}
    assert runner.decode(b'pdf', 'application/pdf')['decoderName'] == 'pypdf'

    probe = SimpleNamespace(duration_seconds=3.5, stream_count=2, width=4, height=5)
    monkeypatch.setattr(runner, 'probe_media_no_network', lambda *_args: probe)
    monkeypatch.setattr(runner, '_ffprobe_version', lambda: '7.1')
    streamed = runner.decode(b'audio', 'audio/mpeg')
    assert streamed['decoderName'] == 'ffprobe'
    assert streamed['measurements'] == {'durationSeconds': 3.5, 'streams': 2, 'pixels': 6}
    with pytest.raises(ValueError, match='request_invalid'):
        runner.decode(b'x', 'text/html')


def test_runner_identity_and_main_fail_closed(monkeypatch):
    monkeypatch.setattr(
        runner.subprocess,
        'run',
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, b'ffprobe version 7.1 Copyright\n', b''
        ),
    )
    assert runner._ffprobe_version() == '7.1'
    monkeypatch.setattr(
        runner.subprocess,
        'run',
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, b'', b''),
    )
    with pytest.raises(ValueError, match='identity_invalid'):
        runner._ffprobe_version()

    monkeypatch.setattr(sys, 'argv', ['runner'])
    assert runner.main() == 64
    monkeypatch.setattr(sys, 'argv', ['runner', 'image/png'])
    monkeypatch.setattr(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(b'x')))
    monkeypatch.setattr(runner, 'decode', lambda *_args: (_ for _ in ()).throw(ValueError()))
    assert runner.main() == 66
    valid = {
        'previewBase64': base64.b64encode(b'p').decode(),
        'preview': {'sha256': hashlib.sha256(b'p').hexdigest()},
    }
    monkeypatch.setattr(runner, 'decode', lambda *_args: valid)
    monkeypatch.setattr(sys, 'stdout', io.StringIO())
    assert runner.main() == 0
    valid['preview']['sha256'] = '0' * 64
    assert runner.main() == 67


def test_scanner_decoder_and_health_protocols_are_strict():
    healthy = subprocess.CompletedProcess(
        [], 0, b'ClamAV 1.4.3/27788/Sun Sep  6 23:00:00 2026\n', b''
    )
    evidence = service._scanner_health(run=lambda *_args, **_kwargs: healthy)
    assert evidence['version'] == '1.4.3' and evidence['definitionsVersion'] == '27788'
    for completed in (
        subprocess.CompletedProcess([], 1, b'', b''),
        subprocess.CompletedProcess([], 0, b'garbage', b''),
        subprocess.CompletedProcess([], 0, b'\xff', b''),
    ):
        with pytest.raises(service.MediaInspectorServiceError):
            service._scanner_health(run=lambda *_args, result=completed, **_kwargs: result)

    assert (
        service._scan(
            b'x',
            run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, b'stdin: OK\n', b''),
        )
        == 'clean'
    )
    assert (
        service._scan(
            b'x',
            run=lambda *_args, **_kwargs: subprocess.CompletedProcess(
                [], 1, b'stdin: Virus FOUND\n', b''
            ),
        )
        == 'infected'
    )
    with pytest.raises(service.MediaInspectorServiceError, match='scanner_response_invalid'):
        service._scan(
            b'x', run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 2, b'', b'')
        )

    decoded = {
        'decoderName': 'pillow',
        'decoderVersion': '1',
        'observedMediaType': 'image/png',
        'measurements': {},
        'preview': {},
        'previewBase64': '',
    }
    outcome = subprocess.CompletedProcess([], 0, json.dumps(decoded).encode(), b'')
    assert service._decode(b'x', 'image/png', run=lambda *_args, **_kwargs: outcome) == decoded
    with pytest.raises(service.MediaInspectorServiceError, match='decoder_response_invalid'):
        service._decode(
            b'x',
            'image/png',
            run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, b'{', b''),
        )


def test_serve_once_writes_terminal_files_and_contains_job_failure(monkeypatch, tmp_path):
    job = tmp_path / 'job'
    job.mkdir()
    (job / 'ready').write_bytes(b'1')
    (job / 'request.json').write_text(json.dumps(request()))
    (job / 'content.bin').write_bytes(b'source')
    monkeypatch.setattr(service, 'inspect_request', lambda *_args, **_kwargs: ({'ok': True}, b'p'))
    assert service.serve_once(tmp_path, key=SIGNING_KEY, build_identity=BUILD_IDENTITY) is True
    assert (job / 'complete').read_bytes() == b'1'
    assert json.loads((job / 'receipt.json').read_text()) == {'ok': True}
    assert service.serve_once(tmp_path, key=SIGNING_KEY, build_identity=BUILD_IDENTITY) is False

    failed_job = tmp_path / 'failed-job'
    failed_job.mkdir()
    (failed_job / 'ready').write_bytes(b'1')
    (failed_job / 'request.json').write_bytes(b'not-json')
    (failed_job / 'content.bin').write_bytes(b'source')
    assert service.serve_once(tmp_path, key=SIGNING_KEY, build_identity=BUILD_IDENTITY) is True
    assert (failed_job / 'failed').read_bytes() == b'media_inspector_failed'


def test_service_main_refuses_missing_process_and_attestation_guards(monkeypatch):
    monkeypatch.setattr(service.os, 'geteuid', lambda: 1000)
    assert service.main() == 69
    monkeypatch.setattr(service.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(
        service.ctypes, 'CDLL', lambda _name: SimpleNamespace(prctl=lambda *_args: 1)
    )
    assert service.main() == 70
    monkeypatch.setattr(
        service.ctypes, 'CDLL', lambda _name: SimpleNamespace(prctl=lambda *_args: 0)
    )
    monkeypatch.delenv('MEDIA_INSPECTOR_SIGNING_KEY', raising=False)
    assert service.main() == 71
    monkeypatch.setenv('MEDIA_INSPECTOR_SIGNING_KEY', base64.urlsafe_b64encode(b'k' * 32).decode())
    monkeypatch.delenv('MEDIA_INSPECTOR_BUILD_IDENTITY', raising=False)
    assert service.main() == 72


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
        assert inspector['healthcheck']['test'] == [
            'CMD', 'python', '-c', 'import os; os.kill(1, 0)'
        ]
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
