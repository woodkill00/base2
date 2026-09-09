from digital_ocean.scripts.python.sanitize_traefik_config import sanitize


def test_redacts_inline_and_list_basic_auth_users_only():
    source = """http:
  middlewares:
    first:
      basicAuth:
        users:
          - 'owner:$2y$05$secret-verifier'
        removeHeader: true
    second:
      basicAuth:
        users: ['operator:{SHA}secret-verifier']
    headers:
      customRequestHeaders:
        X-User: harmless
"""
    result = sanitize(source)
    assert result.count("users: ['REDACTED']") == 2
    assert "secret-verifier" not in result
    assert "removeHeader: true" in result
    assert "X-User: harmless" in result


def test_preserves_non_basic_auth_users_fields():
    source = """users:
  - public-example
http:
  services: {}
"""
    assert sanitize(source) == source
