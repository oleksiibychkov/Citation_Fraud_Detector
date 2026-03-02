"""Tests for watchlist management endpoints."""

from __future__ import annotations


class TestAddToWatchlist:
    def test_add_success(self, client_analyst, mock_repos):
        resp = client_analyst.post(
            "/api/v1/watchlist/add",
            json={"author_id": 1, "reason": "Suspicious patterns"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["author_id"] == 1
        assert data["is_active"] is True

    def test_add_author_not_found(self, client_analyst, mock_repos):
        mock_repos["author"].get_by_id.return_value = None
        resp = client_analyst.post(
            "/api/v1/watchlist/add",
            json={"author_id": 999},
        )
        assert resp.status_code == 404

    def test_add_reader_forbidden(self, client_reader, mock_repos):
        resp = client_reader.post(
            "/api/v1/watchlist/add",
            json={"author_id": 1},
        )
        assert resp.status_code == 403

    def test_add_logs_audit(self, client_analyst, mock_repos):
        client_analyst.post(
            "/api/v1/watchlist/add",
            json={"author_id": 1, "reason": "test"},
        )
        mock_repos["audit"].log.assert_called_once()


class TestListWatchlist:
    def test_list_empty(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_populated(self, client_reader, mock_repos):
        mock_repos["watchlist"].get_active.return_value = [
            {"author_id": 1, "reason": "test", "is_active": True, "created_at": "2024-01-01"},
            {"author_id": 2, "reason": "review", "is_active": True, "created_at": "2024-01-02"},
        ]
        resp = client_reader.get("/api/v1/watchlist")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestSetSensitivity:
    def test_set_sensitivity_success(self, client_analyst, mock_repos):
        mock_repos["watchlist"].set_sensitivity_overrides.return_value = {"author_id": 1}
        resp = client_analyst.put(
            "/api/v1/watchlist/1/sensitivity",
            json={"overrides": {"mcr_threshold": 0.5}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_set_sensitivity_no_entry(self, client_analyst, mock_repos):
        mock_repos["watchlist"].set_sensitivity_overrides.return_value = {}
        resp = client_analyst.put(
            "/api/v1/watchlist/999/sensitivity",
            json={"overrides": {"mcr_threshold": 0.5}},
        )
        assert resp.status_code == 404

    def test_set_sensitivity_invalid_key_rejected(self, client_analyst, mock_repos):
        resp = client_analyst.put(
            "/api/v1/watchlist/1/sensitivity",
            json={"overrides": {"supabase_key": "evil", "mcr_threshold": 0.5}},
        )
        assert resp.status_code == 422

    def test_set_sensitivity_reader_forbidden(self, client_reader, mock_repos):
        resp = client_reader.put(
            "/api/v1/watchlist/1/sensitivity",
            json={"overrides": {"mcr_threshold": 0.5}},
        )
        assert resp.status_code == 403


class TestWatchlistHistory:
    def test_history_empty(self, client_reader, mock_repos):
        resp = client_reader.get("/api/v1/watchlist/1/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_with_snapshots(self, client_reader, mock_repos):
        mock_repos["snapshot"].get_by_author_id.return_value = [
            {
                "snapshot_date": "2024-01-01",
                "fraud_score": 0.35,
                "confidence_level": "moderate",
                "indicator_values": {"SCR": 0.6},
                "algorithm_version": "5.0.0",
            },
        ]
        resp = client_reader.get("/api/v1/watchlist/1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["fraud_score"] == 0.35
