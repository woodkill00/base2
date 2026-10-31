"""Execute the public-family fixture prerequisite without connecting to a database."""

from api.security.content_workspace import CursorCodec
from api.settings import settings
from api.tests import test_workspace_type_keys_postgres as family_tests


def test_family_cursor_is_configured_before_database_fixture_and_restored(monkeypatch):
    monkeypatch.setattr(settings, 'TOKEN_PEPPER', '')
    database_fixture = object()
    requested = []

    class Request:
        def getfixturevalue(self, name):
            requested.append(name)
            # An empty environment must be corrected before requesting DB setup.
            codec = CursorCodec(settings.TOKEN_PEPPER)
            scope = {'site': 'synthetic-site', 'type': 'blog-post'}
            token = codec.encode(scope=scope, position={'id': 'synthetic'}, now=100)
            assert codec.decode(token, expected_scope=scope, now=101) == {'id': 'synthetic'}
            return database_fixture

    with monkeypatch.context() as fixture_patch:
        result = family_tests.public_family_workspace_fixture.__wrapped__(fixture_patch, Request())
        assert result is database_fixture
        assert requested == ['workspace_policy_fixture']
    assert settings.TOKEN_PEPPER == ''
