"""Tests for Supabase client initialization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cfd.config.settings import Settings
from cfd.db.client import get_supabase_client, reset_client


class TestSupabaseClient:
    def setup_method(self):
        reset_client()

    def teardown_method(self):
        reset_client()

    @patch("supabase.create_client")
    def test_creates_client(self, mock_create):
        mock_create.return_value = MagicMock()
        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="key")
        client = get_supabase_client(settings)
        mock_create.assert_called_once_with("https://test.supabase.co", "key")
        assert client is not None

    @patch("supabase.create_client")
    def test_returns_cached(self, mock_create):
        mock_create.return_value = MagicMock()
        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="key")
        c1 = get_supabase_client(settings)
        c2 = get_supabase_client(settings)
        assert c1 is c2
        mock_create.assert_called_once()

    def test_reset_clears_cache(self):
        import cfd.db.client as mod
        mod._client = MagicMock()
        reset_client()
        assert mod._client is None
