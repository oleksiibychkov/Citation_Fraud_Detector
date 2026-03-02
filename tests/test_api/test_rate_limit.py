"""Tests for rate limiting."""

from __future__ import annotations

from cfd.api.rate_limit import _key_func


class TestRateLimitKeyFunc:
    def test_key_from_api_key_header(self):
        class FakeRequest:
            headers = {"x-api-key": "my-key"}
            scope = {"type": "http"}
            client = type("C", (), {"host": "127.0.0.1"})()

        assert _key_func(FakeRequest()) == "my-key"

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
