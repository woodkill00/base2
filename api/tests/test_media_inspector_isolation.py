import base64
import hashlib
import io
import inspect
import json
import os
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
from api.tests import media_inspector_acceptance_entrypoint as acceptance_entrypoint
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


def test_scanner_has_a_separate_bounded_cpu_budget(monkeypatch):
    observed = []
    monkeypatch.setattr(
        service.resource,
        'setrlimit',
        lambda resource_id, limits: observed.append((resource_id, limits)),
    )

    service._limits()
    decoder_cpu = next(
        limits for resource_id, limits in observed if resource_id == service.resource.RLIMIT_CPU
    )
    observed.clear()
    service._scanner_limits()
    scanner_cpu = next(
        limits for resource_id, limits in observed if resource_id == service.resource.RLIMIT_CPU
    )

    assert decoder_cpu == (20, 20)
    assert scanner_cpu == (45, 45)


def test_acceptance_reference_entrypoint_is_explicit_numeric_and_health_only(monkeypatch):
    monkeypatch.setattr(acceptance_entrypoint.sys, 'argv', ['entrypoint'])
    assert acceptance_entrypoint.main() == 64
    monkeypatch.setattr(
        acceptance_entrypoint.sys,
        'argv',
        ['entrypoint', '--reference-epoch', 'not-numeric', '--healthcheck'],
    )
    assert acceptance_entrypoint.main() == 64
    observed = []

    def health(*, now):
        observed.append(now())
        return {'engine': 'clamav'}

    monkeypatch.setattr(acceptance_entrypoint.service, '_scanner_health', health)
    monkeypatch.setattr(
        acceptance_entrypoint.sys,
        'argv',
        ['entrypoint', '--reference-epoch', '1788739200', '--healthcheck'],
    )
    assert acceptance_entrypoint.main() == 0
    assert observed == [datetime.fromtimestamp(1788739200, tz=UTC)]


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
        ({'timeout_seconds': 121}, 'request_invalid'),
        ({'spool_root': 'relative'}, 'isolation_unavailable'),
    ):
        with pytest.raises(MediaInspectorClientError, match=error):
            inspect_media_via_spool(**(common | changes))

    def reject(_delay):
        job = next(path for path in tmp_path.iterdir() if path.is_dir())
        (job / 'failed').write_bytes(b'media_inspection_rejected')

    monkeypatch.setattr(client.time, 'sleep', reject)
    with pytest.raises(MediaInspectorClientError, match='^media_inspection_rejected$'):
        inspect_media_via_spool(**common)
    assert not list(tmp_path.iterdir())

    ticks = iter((0.0, 2.0))
    monkeypatch.setattr(client.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(client.time, 'sleep', lambda _delay: None)
    with pytest.raises(MediaInspectorClientError, match='timeout'):
        inspect_media_via_spool(**common)


@pytest.mark.parametrize(
    ('service_code', 'client_code'),
    [
        ('media_inspection_rejected', 'media_inspection_rejected'),
        ('media_inspector_dependency_unavailable', 'media_inspector_dependency_unavailable'),
    ],
)
def test_service_failure_marker_preserves_bounded_classification(
    monkeypatch, tmp_path, service_code, client_code
):
    content = b'source'
    encoded_verify_key = base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode()
    handled = False

    def fail_job(_delay):
        nonlocal handled
        if handled:
            return
        monkeypatch.setattr(
            service,
            'inspect_request',
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                service.MediaInspectorServiceError(service_code)
            ),
        )
        assert service.serve_once(
            tmp_path,
            key=SIGNING_KEY,
            build_identity=BUILD_IDENTITY,
            producer_uid=os.getuid(),
            producer_gid=os.getgid(),
        ) is True
        handled = True

    monkeypatch.setattr(client.time, 'sleep', fail_job)
    with pytest.raises(MediaInspectorClientError, match=f'^{client_code}$'):
        inspect_media_via_spool(
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
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('marker', [b'unknown_failure', b'x' * 129, b'\xff'])
def test_spool_client_rejects_untrusted_failure_markers(monkeypatch, tmp_path, marker):
    content = b'source'

    def fail_job(_delay):
        job = next(path for path in tmp_path.iterdir() if path.is_dir())
        (job / 'failed').write_bytes(marker)

    monkeypatch.setattr(client.time, 'sleep', fail_job)
    with pytest.raises(MediaInspectorClientError, match='^media_inspector_response_invalid$'):
        inspect_media_via_spool(
            content=content,
            expected_sha256=hashlib.sha256(content).hexdigest(),
            media_type='image/png',
            asset_id=UUID(int=110),
            object_version=1,
            observed_at=NOW,
            spool_root=str(tmp_path),
            encoded_verify_key=base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode(),
            timeout_seconds=1,
        )


def test_spool_client_does_not_follow_failure_marker_symlink(monkeypatch, tmp_path):
    content = b'source'
    outside = tmp_path / 'outside-marker'
    outside.write_bytes(b'media_inspection_rejected')

    def fail_job(_delay):
        job = next(path for path in tmp_path.iterdir() if path.is_dir())
        (job / 'failed').symlink_to(outside)

    monkeypatch.setattr(client.time, 'sleep', fail_job)
    with pytest.raises(MediaInspectorClientError, match='^media_inspector_response_invalid$'):
        inspect_media_via_spool(
            content=content,
            expected_sha256=hashlib.sha256(content).hexdigest(),
            media_type='image/png',
            asset_id=UUID(int=110),
            object_version=1,
            observed_at=NOW,
            spool_root=str(tmp_path),
            encoded_verify_key=base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode(),
            timeout_seconds=1,
        )


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
    evidence = service._scanner_health(
        run=lambda *_args, **_kwargs: healthy,
        now=lambda: datetime(2026, 9, 7, 0, 0, tzinfo=UTC),
    )
    assert evidence['version'] == '1.4.3' and evidence['definitionsVersion'] == '27788'
    with pytest.raises(service.MediaInspectorServiceError, match='definitions_stale'):
        service._scanner_health(
            run=lambda *_args, **_kwargs: healthy,
            now=lambda: datetime(2026, 9, 8, 0, 0, 1, tzinfo=UTC),
        )
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

    scan_call = {}

    def capture_scan(*args, **kwargs):
        scan_call['args'] = args
        scan_call['kwargs'] = kwargs
        return subprocess.CompletedProcess([], 0, b'stdin: OK\n', b'')

    assert service._scan(b'x', run=capture_scan) == 'clean'
    assert scan_call['kwargs']['timeout'] == 50
    assert scan_call['kwargs']['scanner_memory'] is True

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
    job.mkdir(mode=0o700)
    (job / 'ready').write_bytes(b'1')
    (job / 'request.json').write_text(json.dumps(request()))
    (job / 'content.bin').write_bytes(b'source')
    for path in job.iterdir():
        path.chmod(0o600)
    monkeypatch.setattr(service, 'inspect_request', lambda *_args, **_kwargs: ({'ok': True}, b'p'))
    def call():
        return service.serve_once(
            tmp_path,
            key=SIGNING_KEY,
            build_identity=BUILD_IDENTITY,
            producer_uid=os.getuid(),
            producer_gid=os.getgid(),
        )
    assert call() is True
    assert (job / 'complete').read_bytes() == b'1'
    assert json.loads((job / 'receipt.json').read_text()) == {'ok': True}
    assert call() is False

    failed_job = tmp_path / 'failed-job'
    failed_job.mkdir(mode=0o700)
    (failed_job / 'ready').write_bytes(b'1')
    (failed_job / 'request.json').write_bytes(b'not-json')
    (failed_job / 'content.bin').write_bytes(b'source')
    for path in failed_job.iterdir():
        path.chmod(0o600)
    assert call() is True
    assert (failed_job / 'failed').read_bytes() == b'media_inspector_failed'


@pytest.mark.parametrize('special_kind', ['dev-zero-symlink', 'fifo', 'oversized-regular'])
def test_serve_once_rejects_unbounded_and_special_content_without_blocking(tmp_path, special_kind):
    job = tmp_path / special_kind
    job.mkdir(mode=0o700)
    (job / 'ready').write_bytes(b'1')
    (job / 'request.json').write_text(json.dumps(request()))
    (job / 'ready').chmod(0o600)
    (job / 'request.json').chmod(0o600)
    content = job / 'content.bin'
    if special_kind == 'dev-zero-symlink':
        content.symlink_to('/dev/zero')
    elif special_kind == 'fifo':
        os.mkfifo(content, mode=0o600)
    else:
        with content.open('wb') as stream:
            stream.truncate(service.MAX_INPUT_BYTES + 1)
        content.chmod(0o600)
    started = __import__('time').monotonic()
    assert service.serve_once(
        tmp_path,
        key=SIGNING_KEY,
        build_identity=BUILD_IDENTITY,
        producer_uid=os.getuid(),
        producer_gid=os.getgid(),
    ) is True
    assert __import__('time').monotonic() - started < 1
    assert (job / 'failed').read_bytes() == b'media_inspector_request_invalid'


def test_serve_once_ignores_symlinked_or_unsafe_job_directories(tmp_path):
    outside = tmp_path.parent / f'{tmp_path.name}-outside'
    outside.mkdir(mode=0o700)
    (outside / 'ready').write_bytes(b'1')
    (outside / 'ready').chmod(0o600)
    (tmp_path / 'linked-job').symlink_to(outside, target_is_directory=True)
    unsafe = tmp_path / 'unsafe-job'
    unsafe.mkdir(mode=0o777)
    unsafe.chmod(0o777)
    (unsafe / 'ready').write_bytes(b'1')
    assert service.serve_once(
        tmp_path,
        key=SIGNING_KEY,
        build_identity=BUILD_IDENTITY,
        producer_uid=os.getuid(),
        producer_gid=os.getgid(),
    ) is False


def test_stale_claim_recovery_is_bounded_and_removes_only_safe_residue(tmp_path):
    job = tmp_path / 'job'
    job.mkdir(mode=0o700)
    claimed = job / 'claimed'
    temporary = job / 'failed.tmp'
    claimed.write_bytes(b'')
    temporary.write_bytes(b'crash')
    claimed.chmod(0o600)
    temporary.chmod(0o600)
    old = __import__('time').time() - service.CLAIM_STALE_SECONDS - 1
    os.utime(claimed, (old, old))
    os.utime(temporary, (old, old))
    descriptor = os.open(job, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert service._recover_stale_claim(
            descriptor,
            owner_uid=os.getuid(),
            owner_gid=os.getgid(),
            now_seconds=__import__('time').time(),
        )
    finally:
        os.close(descriptor)
    assert not claimed.exists() and not temporary.exists()
    assert service.CLAIM_STALE_SECONDS >= (
        service.MAX_CLIENT_WAIT_SECONDS + service.MAX_INSPECTION_RUNTIME_SECONDS
    )


def test_stale_claim_recovery_stops_streaming_at_seventeenth_entry(monkeypatch, tmp_path):
    job = tmp_path / 'job'
    job.mkdir(mode=0o700)
    claimed = job / 'claimed'
    claimed.write_bytes(b'')
    claimed.chmod(0o600)
    old = __import__('time').time() - service.CLAIM_STALE_SECONDS - 1
    os.utime(claimed, (old, old))

    class EndlessEntries:
        def __init__(self):
            self.closed = False
            self.yielded = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

        def __iter__(self):
            return self

        def __next__(self):
            self.yielded += 1
            return SimpleNamespace(name=f'entry-{self.yielded}')

        def close(self):
            self.closed = True

    entries = EndlessEntries()
    monkeypatch.setattr(service.os, 'scandir', lambda _fd: entries)
    descriptor = os.open(job, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert not service._recover_stale_claim(
            descriptor,
            owner_uid=os.getuid(),
            owner_gid=os.getgid(),
            now_seconds=__import__('time').time(),
        )
    finally:
        os.close(descriptor)
    assert entries.yielded == 17
    assert entries.closed is True
    assert claimed.exists()


@pytest.mark.parametrize('unsafe', ['active', 'symlink', 'fifo', 'foreign', 'oversized'])
def test_claim_recovery_rejects_active_special_foreign_and_oversized_state(tmp_path, unsafe):
    job = tmp_path / unsafe
    job.mkdir(mode=0o700)
    claimed = job / 'claimed'
    if unsafe == 'symlink':
        claimed.symlink_to('/dev/zero')
    else:
        claimed.write_bytes(b'')
        claimed.chmod(0o600)
    old = __import__('time').time() - service.CLAIM_STALE_SECONDS - 1
    if unsafe != 'active':
        os.utime(claimed, (old, old), follow_symlinks=False)
    if unsafe in {'fifo', 'oversized'}:
        temporary = job / 'failed.tmp'
        if unsafe == 'fifo':
            os.mkfifo(temporary, mode=0o600)
        else:
            temporary.write_bytes(b'x' * 129)
            temporary.chmod(0o600)
        os.utime(temporary, (old, old), follow_symlinks=False)
    descriptor = os.open(job, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert not service._recover_stale_claim(
            descriptor,
            owner_uid=os.getuid() + (1 if unsafe == 'foreign' else 0),
            owner_gid=os.getgid(),
            now_seconds=__import__('time').time(),
        )
    finally:
        os.close(descriptor)
    assert claimed.exists() or claimed.is_symlink()


def test_candidate_discovery_has_fixed_raw_scan_cap(tmp_path):
    service._reset_scan_cursor()
    for index in range(service.MAX_SPOOL_SCAN_ENTRIES + 20):
        job = tmp_path / f'job-{index:04d}'
        job.mkdir(mode=0o700)
        ready = job / 'ready'
        ready.write_bytes(b'1')
        ready.chmod(0o600)
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        candidates = service._job_candidates(
            descriptor, owner_uid=os.getuid(), owner_gid=os.getgid()
        )
    finally:
        os.close(descriptor)
    assert len(candidates) == service.MAX_SPOOL_SCAN_ENTRIES
    service._reset_scan_cursor()


def _make_spool_job(root: Path, name: str, *, terminal: bool = False) -> Path:
    job = root / name
    job.mkdir(mode=0o700)
    (job / 'ready').write_bytes(b'1')
    (job / 'ready').chmod(0o600)
    if terminal:
        (job / 'complete').write_bytes(b'1')
        (job / 'complete').chmod(0o600)
    else:
        (job / 'request.json').write_text(json.dumps(request()))
        (job / 'content.bin').write_bytes(b'source')
        (job / 'request.json').chmod(0o600)
        (job / 'content.bin').chmod(0o600)
    return job


def test_cursor_progresses_past_256_preserved_terminal_jobs(monkeypatch, tmp_path):
    service._reset_scan_cursor()
    for index in range(272):
        _make_spool_job(tmp_path, f'preserved-{index:04d}', terminal=True)
    valid = _make_spool_job(tmp_path, 'valid')
    monkeypatch.setattr(service, 'inspect_request', lambda *_a, **_k: ({'ok': True}, b'p'))
    outcomes = [
        service.serve_once(
            tmp_path,
            key=SIGNING_KEY,
            build_identity=BUILD_IDENTITY,
            producer_uid=os.getuid(),
            producer_gid=os.getgid(),
        )
        for _ in range(3)
    ]
    assert any(outcomes) and (valid / 'complete').is_file()
    assert sum((tmp_path / f'preserved-{index:04d}' / 'complete').is_file() for index in range(272)) == 272
    service._reset_scan_cursor()


def test_cursor_handles_new_arrival_deleted_entries_eof_restart_and_fd_cleanup(
    monkeypatch, tmp_path
):
    service._reset_scan_cursor()
    baseline_fds = len(os.listdir('/proc/self/fd'))
    preserved = [
        _make_spool_job(tmp_path, f'blocked-{index:04d}', terminal=True)
        for index in range(300)
    ]
    common = {
        'key': SIGNING_KEY,
        'build_identity': BUILD_IDENTITY,
        'producer_uid': os.getuid(),
        'producer_gid': os.getgid(),
    }
    assert service.serve_once(tmp_path, **common) is False
    for job in preserved:
        __import__('shutil').rmtree(job)
    first = _make_spool_job(tmp_path, 'new-after-delete')
    monkeypatch.setattr(service, 'inspect_request', lambda *_a, **_k: ({'ok': True}, b'p'))
    assert any(service.serve_once(tmp_path, **common) for _ in range(4))
    assert (first / 'complete').is_file()

    # EOF closes the cursor; an arrival after EOF is visible on the next poll.
    assert service.serve_once(tmp_path, **common) is False
    second = _make_spool_job(tmp_path, 'new-after-eof')
    assert service.serve_once(tmp_path, **common) is True
    assert (second / 'complete').is_file()

    # Process restart discards cursor state without touching spool contents.
    service._reset_scan_cursor()
    third = _make_spool_job(tmp_path, 'new-after-restart')
    assert service.serve_once(tmp_path, **common) is True
    assert (third / 'complete').is_file()
    service._reset_scan_cursor()
    assert len(os.listdir('/proc/self/fd')) <= baseline_fds + 1


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
    monkeypatch.setenv('MEDIA_INSPECTOR_BUILD_IDENTITY', BUILD_IDENTITY)
    monkeypatch.setattr(service, '_scanner_health', lambda: {'engine': 'clamav'})
    monkeypatch.delenv('MEDIA_INSPECTOR_SPOOL_PRODUCER_UID', raising=False)
    assert service.main() == 74


def test_service_healthcheck_requires_amd64_and_fresh_scanner(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['media_inspector_service', '--healthcheck'])
    monkeypatch.setattr(service.platform, 'machine', lambda: 'aarch64')
    assert service.main() == 68
    monkeypatch.setattr(service.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(service, '_scanner_health', lambda: {'engine': 'clamav'})
    assert service.main() == 0
    monkeypatch.setattr(
        service,
        '_scanner_health',
        lambda: (_ for _ in ()).throw(
            service.MediaInspectorServiceError('media_scanner_definitions_stale')
        ),
    )
    assert service.main() == 73


def test_main_worker_has_no_decoder_import_and_manifests_isolate_service():
    from api.services import media_library_runtime

    source = inspect.getsource(media_library_runtime).split('def inspect_media_payload', 1)[0]
    assert 'media_library_parser' not in source and 'media_library_processor' not in source
    root = Path(__file__).resolve().parents[2]
    for name in ('local.docker.yml', 'development.docker.yml'):
        manifest = yaml.safe_load((root / name).read_text())
        inspector = manifest['services']['media-inspector']
        spool_init = manifest['services']['media-inspector-spool-init']
        updater = manifest['services']['clamav']
        assert updater['image'] == (
            'clamav/clamav@sha256:'
            '1fdfd24c6f0a0fb60788481487459a6d4eda8a9b448641594e04db8410d34422'
        )
        assert updater['platform'] == 'linux/amd64'
        assert updater['networks'] == ['clamav_egress']
        assert manifest['networks']['clamav_egress']['internal'] is False
        assert [
            service_name
            for service_name, service_config in manifest['services'].items()
            if 'clamav_egress' in service_config.get('networks', [])
        ] == ['clamav']
        assert updater['user'] == '100:101'
        assert updater['entrypoint'] == ['/usr/bin/freshclam']
        assert updater['command'] == [
            '--daemon',
            '--foreground',
            '--stdout',
            '--checks=24',
            '--user=clamav',
            '--config-file=/etc/clamav/freshclam-base2.conf',
        ]
        assert updater['cap_drop'] == ['ALL'] and updater['read_only'] is True
        assert updater['security_opt'] == ['no-new-privileges:true']
        assert updater['pids_limit'] == 32 and updater['mem_limit'] == '1024m'
        assert updater['healthcheck']['test'] == [
            'CMD',
            '/bin/sh',
            '/usr/local/bin/base2-clamav-health',
        ]
        assert updater['healthcheck']['timeout'] == '30s'
        assert './api/config/freshclam.conf:/etc/clamav/freshclam-base2.conf:ro' in updater[
            'volumes'
        ]
        assert (
            './api/scripts/clamav_updater_health.sh:/usr/local/bin/base2-clamav-health:ro'
            in updater['volumes']
        )
        assert inspector['network_mode'] == 'none' and inspector['read_only'] is True
        assert inspector['group_add'] == ['1000']
        assert inspector['platform'] == 'linux/amd64'
        # Docker's default is a private PID namespace. An explicit `private`
        # value is invalid, while omitting `pid` preserves the isolation.
        assert 'pid' not in inspector and inspector['ipc'] == 'private'
        assert (
            inspector['cap_drop'] == ['ALL']
            and inspector['cap_add'] == ['SETUID', 'SETGID', 'SETPCAP']
            and inspector['pids_limit'] == 16
        )
        assert inspector['mem_limit'] == '1536m'
        assert inspector['tmpfs'] == ['/tmp:rw,nosuid,nodev,noexec,size=64m']
        assert inspector['healthcheck']['test'] == [
            'CMD',
            'python',
            '-m',
            'api.services.media_inspector_service',
            '--healthcheck',
        ]
        env = '\n'.join(inspector['environment'])
        assert 'MEDIA_INSPECTOR_SPOOL_PRODUCER_UID=1000' in inspector['environment']
        assert 'MEDIA_INSPECTOR_SPOOL_PRODUCER_GID=1000' in inspector['environment']
        assert spool_init['network_mode'] == 'none' and spool_init['read_only'] is True
        assert spool_init['user'] == '0:0'
        assert spool_init['entrypoint'] == ['/usr/bin/python']
        assert spool_init['command'] == ['/app/api/scripts/media_inspector_spool_init.py']
        assert spool_init['cap_drop'] == ['ALL'] and spool_init['cap_add'] == ['CHOWN']
        assert spool_init['pids_limit'] == 8 and spool_init['mem_limit'] == '32m'
        assert spool_init['restart'] == 'no'
        assert inspector['depends_on']['media-inspector-spool-init']['condition'] == (
            'service_completed_successfully'
        )
        assert manifest['services']['celery-content-worker']['depends_on'][
            'media-inspector-spool-init'
        ]['condition'] == 'service_completed_successfully'
        assert all(
            secret not in env
            for secret in (
                'DB_PASSWORD',
                'TOKEN_PEPPER',
                'IDENTITY_ENCRYPTION_KEY',
                'REDIS_PASSWORD',
            )
        )
        worker = manifest['services']['celery-content-worker']
        assert worker['profiles'] == ['celery']
        assert 'media_inspector_spool:/var/lib/base2/media-inspector' in worker['volumes']
        runtime_worker = manifest['services']['celery-worker']
        assert 'media_inspector_spool:/var/lib/base2/media-inspector' not in runtime_worker['volumes']
        assert '-Q runtime' in runtime_worker['command'][0]
        worker_env = '\n'.join(worker['environment'])
        assert 'MEDIA_INSPECTOR_VERIFY_KEY=' in worker_env
        assert 'MEDIA_INSPECTOR_SIGNING_KEY' not in worker_env
        assert 'MEDIA_INSPECTOR_SIGNING_KEY=' in env
        assert 'MEDIA_INSPECTOR_VERIFY_KEY' not in env


def test_inspector_image_ships_fixed_scanner_and_ffprobe():
    dockerfile = (Path(__file__).resolve().parents[1] / 'Dockerfile.media-inspector').read_text()
    assert 'clamav-1.5.4.linux.x86_64.deb' in dockerfile
    assert '28d6efc5b4423e7830c3559339552eb53870a9eac51ac4efb37d60530d329886' in dockerfile
    assert 'mwader/static-ffmpeg@sha256:54e55b0c' in dockerfile
    assert 'USER root' in dockerfile
    assert 'ENTRYPOINT ["/usr/bin/python"]' in dockerfile
    assert 'CMD ["-m", "api.services.media_inspector_service"]' in dockerfile
    assert 'python@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS privilege-runtime' in dockerfile
    assert 'FROM --platform=linux/amd64 clamav/clamav@sha256:1fdfd24c6f0a0fb60788481487459a6d4eda8a9b448641594e04db8410d34422 AS clamav-definitions' in dockerfile
    assert 'cgr.dev/chainguard/python@sha256:c23539f' in dockerfile
    assert 'cgr.dev/chainguard/python@sha256:1f37785' in dockerfile
    assert 'apk add' not in dockerfile and 'apt-get' not in dockerfile
    assert 'COPY --from=inspector-builder /tmp/clamav/usr/local/bin/clamscan /usr/bin/clamscan' in dockerfile
    assert '/usr/local/etc/certs/clamav.crt' in dockerfile
    assert '/var/lib/clamav/main.cvd' in dockerfile
    assert '/var/lib/clamav/daily.cvd' in dockerfile
    assert '/var/lib/clamav/bytecode.cvd' in dockerfile
    assert '/app/vendor:/app' in inspect.getsource(service._fixed_run)
    assert service.DECODER_ADDRESS_SPACE_BYTES == 640 * 1024 * 1024
    assert service.SCANNER_ADDRESS_SPACE_BYTES == 1024 * 1024 * 1024


def test_updater_health_requires_live_exact_process_signed_fresh_advancing_database():
    root = Path(__file__).resolve().parents[1]
    health = (root / 'scripts/clamav_updater_health.sh').read_text()
    config = (root / 'config/freshclam.conf').read_text()
    acceptance = (root / 'tests/clamav_updater_container_acceptance.sh').read_text()
    assert '/proc/1/comm' in health and "test \"$(cat /proc/1/comm)\" = freshclam" in health
    assert '--checks=24' in health and '--config-file=/etc/clamav/freshclam-base2.conf' in health
    assert 'for suffix in cld cvd' in health
    assert "sigtool --info" in health and "grep -Fqx 'Verification OK.'" in health
    assert 'maximum_age_seconds=86400' in health
    assert '.base2-updater-health' in health and 'definition_version' in health
    assert 'CVDCertsDirectory /etc/clamav/certs' in config
    assert 'TestDatabases yes' in config and 'DatabaseMirror database.clamav.net' in config
    assert '--network none' in acceptance and '--user 100:101' in acceptance
    assert '--checks=1' not in acceptance
    assert 'start_updater 1' in acceptance
    assert '/var/lib/clamav/daily.cvd /var/lib/clamav/daily.cld' in acceptance
    assert 'non-advancing definition set' in acceptance
    assert 'docker_call kill --signal KILL' in acceptance
    assert 'evidence_timeout_seconds=120' in acceptance
    assert 'evidence_safety_margin_seconds=6' in acceptance
    assert 'command_timeout_seconds=30' in acceptance
    assert 'evidence_kill_grace_seconds=5' in acceptance
    assert 'cleanup_timeout_seconds=10' in acceptance
    assert 'cleanup_kill_grace_seconds=5' in acceptance
    assert acceptance.index('evidence_deadline=') < acceptance.index('start_updater 24')
    assert '--kill-after="$evidence_kill_grace_seconds"' in acceptance
    assert 'reject_timeout "$identity_status"' in acceptance
    assert 'reject_timeout "$health_status"' in acceptance
