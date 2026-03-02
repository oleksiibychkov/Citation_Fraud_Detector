"""Tests for API key authentication and role-based access control."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from cfd.api.app import create_app
from cfd.api.auth import APIKeyInfo, _hash_key
from cfd.api.dependencies import get_repos
from cfd.config.settings import Settings


@pytest.fixture
def auth_app():
    """App without auth override (tests real auth flow)."""
    settings = Settings(
        supabase_url="",
        supabase_key="",
        api_keys="valid-key-1,valid-key-2",
    )
    app = create_app(settings)

    mock_repos = {}
    for name in ("author", "fraud_score", "indicator", "citation",
                 "publication", "watchlist", "audit", "algorithm", "snapshot"):
        mock_repos[name] = MagicMock()
    mock_repos["audit"].log.return_value = None
    mock_repos["audit"].get_all.return_value = [
        {"id": 1, "action": "test", "timestamp": "2024-01-01"},
    ]

    app.dependency_overrides[get_repos] = lambda: mock_repos
    return app


def test_missing_api_key_returns_401(auth_app):
    client = TestClient(auth_app)
    resp = client.get("/api/v1/audit")
    assert resp.status_code == 401
    assert "Missing" in resp.json()["detail"]


def test_invalid_api_key_returns_401(auth_app):
    client = TestClient(auth_app)
    resp = client.get("/api/v1/audit", headers={"X-API-Key": "bad-key"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


def test_valid_env_key_returns_admin(auth_app):
    client = TestClient(auth_app)
    resp = client.get("/api/v1/audit", headers={"X-API-Key": "valid-key-1"})
    assert resp.status_code == 200


def test_valid_env_key_second(auth_app):
    client = TestClient(auth_app)
    resp = client.get("/api/v1/audit", headers={"X-API-Key": "valid-key-2"})
    assert resp.status_code == 200


def test_wrong_role_returns_403(auth_app):
    """Env keys get admin role; manually override to test role check."""
    from cfd.api.auth import get_api_key as real_get_api_key

    auth_app.dependency_overrides[real_get_api_key] = lambda: APIKeyInfo(
        key_id=None, name="test", role="reader"
    )
    client = TestClient(auth_app)
    # Audit requires admin
    resp = client.get("/api/v1/audit")
    assert resp.status_code == 403


def test_hash_key_deterministic():
    h1 = _hash_key("test-key")
    h2 = _hash_key("test-key")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_hash_key_different_for_different_keys():
    h1 = _hash_key("key-a")
    h2 = _hash_key("key-b")
    assert h1 != h2


def test_require_role_allows_matching_role(client_admin):
    resp = client_admin.get("/api/v1/audit")
    assert resp.status_code == 200
