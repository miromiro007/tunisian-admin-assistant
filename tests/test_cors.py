"""Tests for CORS: the React dev server may call the API, other origins may not."""
from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)

PREFLIGHT = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


def test_react_dev_origin_is_allowed() -> None:
    origin = "http://127.0.0.1:5173"
    response = client.options("/ask/stream", headers={"Origin": origin, **PREFLIGHT})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_unknown_origin_is_rejected() -> None:
    response = client.options("/ask/stream", headers={"Origin": "http://evil.example", **PREFLIGHT})
    assert "access-control-allow-origin" not in response.headers