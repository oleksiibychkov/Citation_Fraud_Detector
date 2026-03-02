"""Tests for API dependency injection functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from cfd.api.dependencies import get_repos, get_settings, get_supabase
from cfd.config.settings import Settings


class TestGetSettings:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_returns_settings_instance(self):
        result = get_settings()
        assert isinstance(result, Settings)

    def test_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


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
