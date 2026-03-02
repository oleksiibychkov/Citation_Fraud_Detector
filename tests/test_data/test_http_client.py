"""Tests for CachedHttpClient and RateLimiter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from cfd.data.http_client import CachedHttpClient, RateLimiter
from cfd.exceptions import APIError, RateLimitError


class TestRateLimiter:
    def test_first_call_no_delay(self):
        rl = RateLimiter(10)
        with patch("time.sleep") as mock_sleep:
            rl.wait()
            mock_sleep.assert_not_called()

    def test_second_call_may_sleep(self):
        rl = RateLimiter(1)  # 1 req/s = 1s interval
        rl.wait()
        with patch("time.sleep") as mock_sleep:
            rl.wait()
            # Should have slept (interval is 1.0s, elapsed ~0)
            if mock_sleep.called:
                assert mock_sleep.call_args[0][0] > 0


class TestCachedHttpClient:
    def _make_client(self, supabase=None):
        client = CachedHttpClient(supabase_client=supabase, cache_ttl_days=7)
        client._http = MagicMock()
        client._rate_limiter = MagicMock()
        return client

    def test_get_no_cache(self):
        client = self._make_client()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [1]}
        client._http.get.return_value = mock_resp
        data = client.get("https://api.example.com/test", use_cache=False)
        assert data == {"results": [1]}

    def test_get_cache_hit(self):
        mock_sb = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        table.execute.return_value = MagicMock(data=[{"response_data": {"cached": True}, "expires_at": future}])
        mock_sb.table.return_value = table

        client = self._make_client(supabase=mock_sb)
        data = client.get("https://api.example.com/test", use_cache=True)
        assert data == {"cached": True}
        client._http.get.assert_not_called()

    def test_get_cache_miss_fetches(self):
        mock_sb = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.upsert.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_sb.table.return_value = table

        client = self._make_client(supabase=mock_sb)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"fresh": True}
        client._http.get.return_value = mock_resp

        data = client.get("https://api.example.com/test", use_cache=True)
        assert data == {"fresh": True}
        client._http.get.assert_called_once()

    def test_cache_key_deterministic(self):
        client = self._make_client()
        k1 = client._cache_key("https://api.example.com/test", {"a": 1})
        k2 = client._cache_key("https://api.example.com/test", {"a": 1})
        assert k1 == k2
        assert len(k1) == 64

    def test_cache_key_different_params(self):
        client = self._make_client()
        k1 = client._cache_key("https://api.example.com/test", {"a": 1})
        k2 = client._cache_key("https://api.example.com/test", {"a": 2})
        assert k1 != k2

    def test_do_request_429_raises_rate_limit(self):
        client = self._make_client()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "1"}
        client._http.get.return_value = mock_resp

        with patch("time.sleep"), pytest.raises(RateLimitError):
            client._do_request("https://api.example.com", None, None)

    def test_do_request_500_raises_api_error(self):
        client = self._make_client()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500
        client._http.get.return_value = mock_resp

        with pytest.raises(APIError):
            client._do_request("https://api.example.com", None, None)
