import json
from fastapi.testclient import TestClient
from api.main import app
from api.tests.test_content_workspace_records_contract import FakeRecordRepository, scoped  # noqa: F401

URL = '/api/content/v1/types/article/records'
HEADERS = {'Authorization': 'Bearer synthetic', 'X-Tenant-ID': 'site-a'}


def test_atomic_public_copy_request_forwarding_clear_and_omission():
    client = TestClient(app)
    copy = {'excerpt': 'Summary', 'body': '<script>literal</script>\n\nPublic body'}
    created = client.post(
        URL,
        headers=HEADERS,
        json={
            'slug': 'hello',
            'title': 'Hello',
            'values': {'title': 'PRIVATE'},
            'publicContent': copy,
        },
    )
    assert created.status_code == 201
    assert FakeRecordRepository.calls[-1][1]['payload']['public_content'] == copy
    url = URL + '/' + created.json()['id']
    cleared = client.patch(
        url,
        headers=HEADERS,
        json={
            'values': {'title': 'PRIVATE'},
            'expectedVersion': 1,
            'publicContent': {'excerpt': '', 'body': ''},
        },
    )
    assert cleared.status_code == 200
    assert FakeRecordRepository.calls[-1][1]['public_content'] == {'excerpt': '', 'body': ''}
    assert (
        client.patch(url, headers={**HEADERS, 'If-Match': '"2"'}, json={'values': {}}).status_code
        == 200
    )
    assert FakeRecordRepository.calls[-1][1]['public_content'] is None
    assert (
        client.patch(url, headers=HEADERS, json={'values': {}, 'publicContent': copy}).status_code
        == 428
    )


def test_surrogate_and_nul_rejection_is_422_without_echoing_content_or_calling_repository():
    client = TestClient(app)
    for invalid in ('\ud800', '\0', False, None):
        payload = {
            'slug': 'hello',
            'title': 'Hello',
            'publicContent': {'excerpt': 'PRIVATE', 'body': invalid},
        }
        response = client.post(
            URL,
            headers={**HEADERS, 'Content-Type': 'application/json'},
            content=json.dumps(payload, ensure_ascii=True),
        )
        assert response.status_code == 422
        assert 'PRIVATE' not in response.text
    assert FakeRecordRepository.calls == []
