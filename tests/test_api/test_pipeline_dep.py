"""Tests for get_pipeline API dependency."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cfd.api.dependencies import get_pipeline
from cfd.config.settings import Settings


class TestGetPipeline:
    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.data.openalex.OpenAlexStrategy")
    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    def test_pipeline_no_db(self, mock_rl, mock_http, mock_strategy, mock_pipeline):
        request = MagicMock()
        request.app.state.supabase = None
        settings = Settings(supabase_url="", supabase_key="")

        get_pipeline(request, settings)

        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["author_repo"] is None
        assert call_kwargs["score_repo"] is None

    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.data.openalex.OpenAlexStrategy")
    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    def test_pipeline_with_db(self, mock_rl, mock_http, mock_strategy, mock_pipeline):
        request = MagicMock()
        request.app.state.supabase = MagicMock()
        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="key")

        get_pipeline(request, settings)

        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["author_repo"] is not None
        assert call_kwargs["pub_repo"] is not None
        assert call_kwargs["cit_repo"] is not None
        assert call_kwargs["ind_repo"] is not None
        assert call_kwargs["score_repo"] is not None

    @patch("cfd.analysis.pipeline.AnalysisPipeline")
    @patch("cfd.data.openalex.OpenAlexStrategy")
    @patch("cfd.data.http_client.CachedHttpClient")
    @patch("cfd.data.http_client.RateLimiter")
    @patch("cfd.db.repositories.authors.AuthorRepository", side_effect=Exception("DB fail"))
    def test_pipeline_db_init_fails(self, mock_repo, mock_rl, mock_http, mock_strategy, mock_pipeline):
        request = MagicMock()
        request.app.state.supabase = MagicMock()
        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="key")

        get_pipeline(request, settings)

        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["author_repo"] is None
