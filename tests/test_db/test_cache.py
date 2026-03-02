"""Tests for ApiCache."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from cfd.db.cache import ApiCache


def _make_cache():
    client = MagicMock()
    table = MagicMock()
    for m in ("select", "upsert", "delete", "eq", "lt"):
        getattr(table, m).return_value = table
    execute_result = MagicMock()
    execute_result.data = []
    table.execute.return_value = execute_result
    client.table.return_value = table
    return ApiCache(client, ttl_days=7), client


class TestMakeKey:
    def test_deterministic(self):
        k1 = ApiCache.make_key("https://api.example.com", {"a": 1})
        k2 = ApiCache.make_key("https://api.example.com", {"a": 1})
        assert k1 == k2
        assert len(k1) == 64

    def test_different_params(self):
        k1 = ApiCache.make_key("https://api.example.com", {"a": 1})
        k2 = ApiCache.make_key("https://api.example.com", {"a": 2})
        assert k1 != k2

    def test_none_params(self):
        k1 = ApiCache.make_key("https://api.example.com", None)
        k2 = ApiCache.make_key("https://api.example.com", {})
        assert k1 == k2


class TestCacheGet:
    def test_hit(self):
        cache, client = _make_cache()
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        table = client.table.return_value
        table.execute.return_value = MagicMock(
            data=[{"response_data": {"cached": True}, "expires_at": future}]
        )
        result = cache.get("key123")
        assert result == {"cached": True}

    def test_expired(self):
        cache, client = _make_cache()
        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        table = client.table.return_value
        table.execute.return_value = MagicMock(
            data=[{"response_data": {"old": True}, "expires_at": past}]
        )
        result = cache.get("key123")
        assert result is None

    def test_miss(self):
        cache, _client = _make_cache()
        assert cache.get("nonexistent") is None


class TestCacheSet:
    def test_stores(self):
        cache, client = _make_cache()
        cache.set("key1", "https://api.example.com", {"a": 1}, {"data": 1}, "scopus")
        client.table.return_value.upsert.assert_called_once()


class TestCacheInvalidate:
    def test_deletes(self):
        cache, client = _make_cache()
        cache.invalidate("key1")
        client.table.return_value.delete.assert_called_once()


class TestCleanupExpired:
    def test_returns_count(self):
        cache, client = _make_cache()
        table = client.table.return_value
        table.execute.return_value = MagicMock(data=[{"id": 1}, {"id": 2}])
        count = cache.cleanup_expired()
        assert count == 2

    def test_returns_zero_on_empty(self):
        cache, _client = _make_cache()
        assert cache.cleanup_expired() == 0
