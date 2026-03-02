"""Shared fixtures for API tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from cfd.api.app import create_app
from cfd.api.auth import APIKeyInfo, get_api_key
from cfd.api.dependencies import get_repos, get_settings, get_supabase
from cfd.config.settings import Settings


@pytest.fixture
def api_settings():
    """Test settings for API."""
    return Settings(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        api_keys="test-api-key-1,test-api-key-2",
    )


def _make_key_info(role: str = "admin") -> APIKeyInfo:
    return APIKeyInfo(key_id=1, name="test_key", role=role)


@pytest.fixture
def mock_repos():
    """Mock all repository objects."""
    repos = {}
    for name in (
        "author", "fraud_score", "indicator", "citation",
        "publication", "watchlist", "audit", "algorithm", "snapshot",
    ):
        repos[name] = MagicMock()

    # Default return values
    repos["author"].get_by_id.return_value = {
        "id": 1,
        "surname": "Ivanenko",
        "full_name": "Oleksandr Ivanenko",
        "scopus_id": "57200000001",
        "orcid": "0000-0002-1234-5678",
        "institution": "Kyiv National University",
        "discipline": "Computer Science",
        "h_index": 15,
        "publication_count": 50,
        "citation_count": 500,
    }
    repos["fraud_score"].get_latest_by_author.return_value = {
        "score": 0.42,
        "confidence_level": "moderate",
        "triggered_indicators": ["SCR", "MCR"],
    }
    repos["indicator"].get_by_author_id.return_value = [
        {"indicator_type": "SCR", "value": 0.65, "details": {"self_rate": 0.65}},
        {"indicator_type": "MCR", "value": 0.45, "details": {}},
    ]
    repos["citation"].get_by_target_author.return_value = [
        {"source_work_id": "W1", "target_work_id": "W2"},
        {"source_work_id": "W3", "target_work_id": "W2"},
    ]
    repos["watchlist"].get_active.return_value = []
    repos["watchlist"].add.return_value = {
        "author_id": 1, "reason": "test", "notes": None, "is_active": True, "created_at": "2024-01-01",
    }
    repos["snapshot"].get_by_author_id.return_value = []
    repos["audit"].get_all.return_value = []
    repos["audit"].log.return_value = None
    repos["algorithm"].get_by_version.return_value = {
        "version": "5.0.0", "release_date": "2024-01-01", "indicator_count": 20,
    }
    repos["algorithm"].get_all.return_value = [
        {"version": "5.0.0", "release_date": "2024-01-01", "indicator_count": 20},
    ]
    return repos


@pytest.fixture
def app(api_settings, mock_repos):
    """Create test app with dependency overrides."""
    test_app = create_app(api_settings)

    def _override_settings():
        return api_settings

    def _override_repos():
        return mock_repos

    def _override_supabase():
        return MagicMock()

    test_app.dependency_overrides[get_settings] = _override_settings
    test_app.dependency_overrides[get_repos] = _override_repos
    test_app.dependency_overrides[get_supabase] = _override_supabase
    return test_app


@pytest.fixture
def override_auth_reader(app):
    """Override auth to return reader role."""
    app.dependency_overrides[get_api_key] = lambda: _make_key_info("reader")
    return app


@pytest.fixture
def override_auth_analyst(app):
    """Override auth to return analyst role."""
    app.dependency_overrides[get_api_key] = lambda: _make_key_info("analyst")
    return app


@pytest.fixture
def override_auth_admin(app):
    """Override auth to return admin role."""
    app.dependency_overrides[get_api_key] = lambda: _make_key_info("admin")
    return app


@pytest.fixture
def client_reader(override_auth_reader):
    """Test client with reader auth."""
    return TestClient(override_auth_reader)


@pytest.fixture
def client_analyst(override_auth_analyst):
    """Test client with analyst auth."""
    return TestClient(override_auth_analyst)


@pytest.fixture
def client_admin(override_auth_admin):
    """Test client with admin auth."""
    return TestClient(override_auth_admin)


@pytest.fixture
def client_no_auth(app):
    """Test client with no auth override (requires real API key)."""
    return TestClient(app)
