from __future__ import annotations

import pytest

from api.security.content_workspace import CursorCodec, CursorError, canonical_digest


def test_cursor_is_opaque_expiring_and_bound_to_exact_scope():
    codec = CursorCodec('synthetic-test-secret-104')
    scope = {
        'site': 'site-a',
        'type': 'article',
        'query': canonical_digest({'sort': 'slug'}),
        'limit': 25,
    }
    token = codec.encode(scope=scope, position={'slug': 'hello', 'id': 'record-a'}, now=100)
    assert 'site-a' not in token
    assert codec.decode(token, expected_scope=scope, now=101) == {'slug': 'hello', 'id': 'record-a'}
    with pytest.raises(CursorError):
        codec.decode(token, expected_scope={**scope, 'site': 'site-b'}, now=101)
    with pytest.raises(CursorError):
        codec.decode(token, expected_scope=scope, now=1_001)
    with pytest.raises(CursorError):
        codec.decode(token[:-1] + ('A' if token[-1] != 'A' else 'B'), expected_scope=scope, now=101)


def test_cursor_configuration_rejects_weak_secrets_and_unbounded_ttl():
    with pytest.raises(ValueError, match='cursor_configuration_invalid'):
        CursorCodec('short')
    with pytest.raises(ValueError, match='cursor_configuration_invalid'):
        CursorCodec('synthetic-test-secret-104', ttl_seconds=86_400)
