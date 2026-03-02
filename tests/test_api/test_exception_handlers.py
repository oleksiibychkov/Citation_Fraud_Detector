"""Tests for FastAPI exception handlers defined in app.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from cfd.api.app import create_app
from cfd.api.auth import get_api_key
from cfd.config.settings import Settings
from cfd.exceptions import (
    AuthorizationError,
    AuthorNotFoundError,
    CFDError,
    DatabaseUnavailableError,
    RateLimitError,
    ValidationError,
)


def _make_app(exc_to_raise: Exception):
    """Create a test app with a route that raises the given exception."""
    settings = Settings(supabase_url="", supabase_key="")
    app = create_app(settings)

    @app.get("/test-exc")
    async def _raise_exc():
        raise exc_to_raise

    app.dependency_overrides[get_api_key] = lambda: MagicMock(key_id=1, name="test", role="admin")
    return app


def test_author_not_found_returns_404():
    app = _make_app(AuthorNotFoundError("Author X not found"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-exc")
    assert resp.status_code == 404
    assert "Author X not found" in resp.json()["detail"]


def test_validation_error_returns_422():
    app = _make_app(ValidationError("Invalid ORCID"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-exc")
    assert resp.status_code == 422
    assert "Invalid ORCID" in resp.json()["detail"]


def test_authorization_error_returns_403():
    app = _make_app(AuthorizationError("Forbidden"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-exc")
    assert resp.status_code == 403


def test_rate_limit_error_returns_429():
    app = _make_app(RateLimitError("Too fast"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-exc")
    assert resp.status_code == 429


def test_db_unavailable_returns_503():
    app = _make_app(DatabaseUnavailableError("DB down"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-exc")
    assert resp.status_code == 503


def test_generic_cfd_error_returns_500():
    app = _make_app(CFDError("Something broke"))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-exc")
    assert resp.status_code == 500
    # Sanitized — internal error details are not exposed to client
    assert resp.json()["detail"] == "Internal server error"
