"""Tests for rate limiting."""

from __future__ import annotations

from cfd.api.rate_limit import _key_func


class TestRateLimitKeyFunc:
    def test_key_from_api_key_header_is_hashed(self):
        class FakeRequest:
            headers = {"x-api-key": "my-key"}
            scope = {"type": "http"}
            client = type("C", (), {"host": "127.0.0.1"})()

        result = _key_func(FakeRequest())
        # Should be a full hex hash, not the raw key
        assert result != "my-key"
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_key_fallback_to_ip(self):
        class FakeRequest:
            headers = {}
            scope = {"type": "http"}
            client = type("C", (), {"host": "192.168.1.1"})()

        result = _key_func(FakeRequest())
        assert result == "192.168.1.1"

    def test_key_empty_header_falls_back(self):
        class FakeRequest:
            headers = {"x-api-key": ""}
            scope = {"type": "http"}
            client = type("C", (), {"host": "10.0.0.1"})()

        result = _key_func(FakeRequest())
        assert result == "10.0.0.1"
