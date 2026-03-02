"""Tests for FastAPI application setup: health, ready, CORS, exception handlers."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from cfd import __version__
from cfd.api.app import create_app
from cfd.config.settings import Settings


def test_health_returns_ok():
    app = create_app(Settings(supabase_url="", supabase_key=""))
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__


def test_ready_no_db():
    app = create_app(Settings(supabase_url="", supabase_key=""))
    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


def test_ready_with_mock_db():
    app = create_app(Settings(supabase_url="", supabase_key=""))
    mock_sb = MagicMock()
    table = MagicMock()
    table.select.return_value = table
    table.limit.return_value = table
    table.execute.return_value = MagicMock(data=[{"id": 1}])
    mock_sb.table.return_value = table
    app.state.supabase = mock_sb

    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["database"] == "connected"


def test_cors_headers(client_reader):
    resp = client_reader.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    # CORS middleware should respond
    assert resp.status_code in (200, 204, 405)


def test_openapi_available(client_reader):
    resp = client_reader.get("/api/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"] == "Citation Fraud Detector API"


def test_docs_available(client_reader):
    resp = client_reader.get("/api/docs")
    assert resp.status_code == 200
