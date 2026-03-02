"""Tests for algorithm version endpoints."""

from __future__ import annotations


class TestCurrentVersion:
    def test_get_current(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/version/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "5.0.0"
        assert data["indicator_count"] == 22

    def test_current_not_found_returns_default(self, client_reader, mock_repos):
        mock_repos["algorithm"].get_by_version.return_value = None
        resp = client_reader.get("/api/v1/version/current")
        assert resp.status_code == 200
        assert resp.json()["version"] != ""


class TestVersionHistory:
    def test_history_list(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/version/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["version"] == "5.0.0"

    def test_history_empty(self, client_reader, mock_repos):
        mock_repos["algorithm"].get_all.return_value = []
        resp = client_reader.get("/api/v1/version/history")
        assert resp.status_code == 200
        assert resp.json() == []
