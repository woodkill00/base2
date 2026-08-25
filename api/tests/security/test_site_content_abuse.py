from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.site_content import get_site_content_service
from api.settings import settings

from api.security.public_content import (
    FormPolicyError,
    MediaPolicyError,
    inspect_media_upload,
    validate_form_submission,
)


def test_form_payload_rejects_oversize_depth_controls_and_honeypot():
    with pytest.raises(FormPolicyError, match='payload_value_too_large'):
        validate_form_submission({'message': 'x' * 33_000}, {})
    with pytest.raises(FormPolicyError, match='payload_too_deep'):
        validate_form_submission({'a': {'b': {'c': {'d': {'e': 'x'}}}}}, {})
    with pytest.raises(FormPolicyError, match='payload_control_character'):
        validate_form_submission({'message': 'hello\x00world'}, {})
    with pytest.raises(FormPolicyError, match='spam_rejected'):
        validate_form_submission({'message': 'hello', '_gotcha': 'robot'}, {})


def test_form_payload_normalizes_keys_and_requires_bounded_consent():
    payload, consent = validate_form_submission(
        {'message': '  hello  ', 'email': 'person@example.test'},
        {'essential': True},
    )
    assert payload == {'email': 'person@example.test', 'message': 'hello'}
    assert consent == {'essential': True}
    with pytest.raises(FormPolicyError, match='payload_key_invalid'):
        validate_form_submission({'../message': 'hello'}, {})


@pytest.mark.parametrize(
    ('content', 'claimed', 'expected'),
    [
        (b'\x89PNG\r\n\x1a\n' + b'x' * 20, 'image/png', 'image/png'),
        (b'\xff\xd8\xff' + b'x' * 20, 'image/jpeg', 'image/jpeg'),
        (b'%PDF-1.7\n' + b'x' * 20, 'application/pdf', 'application/pdf'),
    ],
)
def test_media_signature_controls_type_and_returns_quarantine_first(content, claimed, expected):
    receipt = inspect_media_upload(
        content,
        original_name='field-note.bin',
        claimed_type=claimed,
        allowed_types={expected},
        max_bytes=1024,
        attribution='Owner supplied',
    )
    assert receipt.sniffed_type == expected
    assert receipt.status == 'quarantined'
    assert receipt.sha256
    assert receipt.metadata == {'metadataPolicy': 'stripped'}


def test_media_rejects_spoof_size_name_type_and_attribution():
    png = b'\x89PNG\r\n\x1a\n' + b'x' * 20
    with pytest.raises(MediaPolicyError, match='mime_mismatch'):
        inspect_media_upload(png, original_name='a.png', claimed_type='image/jpeg', allowed_types={'image/png'}, max_bytes=100)
    with pytest.raises(MediaPolicyError, match='media_too_large'):
        inspect_media_upload(png, original_name='a.png', claimed_type='image/png', allowed_types={'image/png'}, max_bytes=8)
    with pytest.raises(MediaPolicyError, match='filename_invalid'):
        inspect_media_upload(png, original_name='../a.png', claimed_type='image/png', allowed_types={'image/png'}, max_bytes=100)
    with pytest.raises(MediaPolicyError, match='media_type_forbidden'):
        inspect_media_upload(b'MZ' + b'x' * 20, original_name='a.exe', claimed_type='application/octet-stream', allowed_types={'image/png'}, max_bytes=100)
    with pytest.raises(MediaPolicyError, match='attribution_too_large'):
        inspect_media_upload(png, original_name='a.png', claimed_type='image/png', allowed_types={'image/png'}, max_bytes=100, attribution='x' * 2001)


class _FormService:
    def submit_form(self, **_kwargs):
        return {
            'id': '22222222-2222-4222-8222-222222222222',
            'status': 'queued',
            'replayed': False,
            'receivedAt': '2026-08-25T00:00:00Z',
        }


def test_form_route_rate_limit_and_session_csrf_fail_closed(monkeypatch):
    app.dependency_overrides[get_site_content_service] = _FormService
    client = TestClient(app)
    headers = {'X-Tenant-Id': 'site-a', 'Idempotency-Key': 'request-1'}
    try:
        monkeypatch.setattr(
            'api.routes.site_content.rate_limit.incr_and_check_detailed',
            lambda *_args: (11, True, 37),
        )
        limited = client.post('/api/forms/contact', headers=headers, json={'payload': {}})
        assert limited.status_code == 429
        assert limited.headers['Retry-After'] == '37'

        monkeypatch.setattr(
            'api.routes.site_content.rate_limit.incr_and_check_detailed',
            lambda *_args: (1, False, 0),
        )
        client.cookies.set(settings.SESSION_COOKIE_NAME, 'private-session')
        client.cookies.set(settings.CSRF_COOKIE_NAME, 'expected')
        rejected = client.post('/api/forms/contact', headers=headers, json={'payload': {}})
        assert rejected.status_code == 403
        assert rejected.json() == {'detail': 'csrf_failed'}
        accepted = client.post(
            '/api/forms/contact',
            headers={**headers, 'X-CSRF-Token': 'expected'},
            json={'payload': {}},
        )
        assert accepted.status_code == 202
    finally:
        app.dependency_overrides.clear()
