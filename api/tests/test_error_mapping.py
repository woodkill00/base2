from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.errors import register_error_handlers
from api.exceptions import UpstreamTimeout, UpstreamBadResponse, ConfigError


def make_app():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/timeout")
    def raise_timeout():
        raise UpstreamTimeout("timeout")

    @app.get("/bad")
    def raise_bad():
        raise UpstreamBadResponse("bad")

    @app.get("/config")
    def raise_config():
        raise ConfigError("bad config")

    @app.get("/validate")
    def needs_int_param(q: int):  # missing or wrong type should yield 422
        return {"q": q}

    return app


def test_upstream_timeout_maps_to_504():
    app = make_app()
    client = TestClient(app)
    r = client.get("/timeout")
    assert r.status_code == 504
    assert r.json().get("detail") == "upstream_timeout"


def test_upstream_bad_response_maps_to_502():
    app = make_app()
    client = TestClient(app)
    r = client.get("/bad")
    assert r.status_code == 502
    assert r.json().get("detail") == "upstream_bad_response"


def test_config_error_maps_to_500():
    app = make_app()
    client = TestClient(app)
    r = client.get("/config")
    assert r.status_code == 500
    assert r.json().get("detail") == "configuration_error"


def test_validation_error_maps_to_422():
    app = make_app()
    client = TestClient(app)
    r = client.get("/validate")
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
