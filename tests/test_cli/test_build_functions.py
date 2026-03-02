"""Tests for _build_strategy and _build_pipeline helper functions in cli/main.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cfd.config.settings import Settings


@pytest.fixture
def settings_no_db():
    return Settings(supabase_url="", supabase_key="", scopus_api_key="")


@pytest.fixture
def settings_with_scopus():
    return Settings(supabase_url="", supabase_key="", scopus_api_key="test-scopus-key")


@pytest.fixture
def settings_with_db():
    return Settings(supabase_url="https://test.supabase.co", supabase_key="test-key", scopus_api_key="")


class TestBuildStrategy:
    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    def test_openalex_source(self, mock_rl, mock_http, settings_no_db):
        from cfd.cli.main import _build_strategy

        strategy = _build_strategy("openalex", settings_no_db)
        from cfd.data.openalex import OpenAlexStrategy

        assert isinstance(strategy, OpenAlexStrategy)

    @patch("cfd.data.scopus.ScopusStrategy")
    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    def test_scopus_source(self, mock_rl, mock_http, mock_scopus_cls, settings_with_scopus):
        from cfd.cli.main import _build_strategy

        mock_scopus_cls.return_value = MagicMock()
        _build_strategy("scopus", settings_with_scopus)
        mock_scopus_cls.assert_called_once()

    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    def test_auto_source_no_scopus(self, mock_rl, mock_http, settings_no_db):
        from cfd.cli.main import _build_strategy

        strategy = _build_strategy("auto", settings_no_db)
        from cfd.data.openalex import OpenAlexStrategy

        assert isinstance(strategy, OpenAlexStrategy)

    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    def test_auto_source_with_scopus(self, mock_rl, mock_http, settings_with_scopus):
        from cfd.cli.main import _build_strategy

        strategy = _build_strategy("auto", settings_with_scopus)
        from cfd.data.fallback import FallbackStrategy

        assert isinstance(strategy, FallbackStrategy)

    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    @patch("cfd.db.client.get_supabase_client")
    def test_with_supabase_client(self, mock_supa, mock_rl, mock_http, settings_with_db):
        from cfd.cli.main import _build_strategy

        mock_supa.return_value = MagicMock()
        _build_strategy("openalex", settings_with_db)
        mock_supa.assert_called_once_with(settings_with_db)

    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    @patch("cfd.db.client.get_supabase_client", side_effect=Exception("DB down"))
    def test_supabase_fails_gracefully(self, mock_supa, mock_rl, mock_http, settings_with_db):
        from cfd.cli.main import _build_strategy

        strategy = _build_strategy("openalex", settings_with_db)
        assert strategy is not None


class TestBuildPipeline:
    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    def test_no_db(self, mock_pipeline_cls, settings_no_db):
        from cfd.cli.main import _build_pipeline

        mock_strategy = MagicMock()
        _build_pipeline(mock_strategy, settings_no_db)
        mock_pipeline_cls.assert_called_once()
        call_kwargs = mock_pipeline_cls.call_args[1]
        assert call_kwargs["author_repo"] is None
        assert call_kwargs["score_repo"] is None

    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.db.client.get_supabase_client")
    def test_with_db(self, mock_supa, mock_pipeline_cls, settings_with_db):
        from cfd.cli.main import _build_pipeline

        mock_supa.return_value = MagicMock()
        mock_strategy = MagicMock()
        _build_pipeline(mock_strategy, settings_with_db)
        call_kwargs = mock_pipeline_cls.call_args[1]
        assert call_kwargs["author_repo"] is not None
        assert call_kwargs["score_repo"] is not None

    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.db.client.get_supabase_client", side_effect=Exception("DB fail"))
    def test_db_fails_gracefully(self, mock_supa, mock_pipeline_cls, settings_with_db):
        from cfd.cli.main import _build_pipeline

        mock_strategy = MagicMock()
        _build_pipeline(mock_strategy, settings_with_db)
        call_kwargs = mock_pipeline_cls.call_args[1]
        assert call_kwargs["author_repo"] is None
