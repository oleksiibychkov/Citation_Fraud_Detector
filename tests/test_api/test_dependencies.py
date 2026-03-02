"""Tests for API dependency injection functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from cfd.api.dependencies import get_repos, get_settings, get_supabase
from cfd.config.settings import Settings


class TestGetSettings:
    def test_returns_settings_from_app_state(self):
        custom = Settings(supabase_url="https://test.co", supabase_key="key")
        request = MagicMock()
        request.app.state.settings = custom
        result = get_settings(request)
        assert result is custom

    def test_returns_default_when_no_state(self):
        request = MagicMock()
        request.app.state.settings = None
        result = get_settings(request)
        assert isinstance(result, Settings)


class TestGetSupabase:
    def test_returns_client(self):
        request = MagicMock()
        request.app.state.supabase = MagicMock()
        result = get_supabase(request)
        assert result is request.app.state.supabase

    def test_raises_503_when_none(self):
        request = MagicMock()
        request.app.state.supabase = None
        with pytest.raises(HTTPException) as exc_info:
            get_supabase(request)
        assert exc_info.value.status_code == 503


class TestGetRepos:
    def test_returns_all_nine(self):
        client = MagicMock()
        repos = get_repos(client=client)
        expected_keys = {
            "author", "fraud_score", "indicator", "citation",
            "publication", "watchlist", "audit", "algorithm", "snapshot",
        }
        assert set(repos.keys()) == expected_keys
        for key, repo in repos.items():
            assert repo is not None, f"Repo '{key}' should not be None"
