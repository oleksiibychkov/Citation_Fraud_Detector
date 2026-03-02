"""Tests for I18n middleware."""

from __future__ import annotations

from unittest.mock import patch


class TestI18nMiddleware:
    def test_english_accept_language(self, client_reader):
        with patch("cfd.api.middleware.set_language") as mock_set:
            client_reader.get("/health", headers={"Accept-Language": "en-US,en;q=0.9"})
            mock_set.assert_called_with("en")

    def test_ukrainian_accept_language(self, client_reader):
        with patch("cfd.api.middleware.set_language") as mock_set:
            client_reader.get("/health", headers={"Accept-Language": "uk-UA"})
            mock_set.assert_called_with("ua")

    def test_no_accept_language_defaults_ua(self, client_reader):
        with patch("cfd.api.middleware.set_language") as mock_set:
            client_reader.get("/health")
            mock_set.assert_called_with("ua")

    def test_french_accept_language_defaults_ua(self, client_reader):
        with patch("cfd.api.middleware.set_language") as mock_set:
            client_reader.get("/health", headers={"Accept-Language": "fr-FR"})
            mock_set.assert_called_with("ua")

    def test_empty_accept_language(self, client_reader):
        with patch("cfd.api.middleware.set_language") as mock_set:
            client_reader.get("/health", headers={"Accept-Language": ""})
            mock_set.assert_called_with("ua")
