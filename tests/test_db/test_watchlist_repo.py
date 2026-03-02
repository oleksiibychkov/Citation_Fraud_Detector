"""Tests for WatchlistRepository."""

from __future__ import annotations

from cfd.db.repositories.watchlist import WatchlistRepository

from .conftest import set_execute_data


class TestWatchlistRepository:
    def test_add(self, mock_client):
        set_execute_data(mock_client, [{"author_id": 1, "is_active": True}])
        repo = WatchlistRepository(mock_client)
        result = repo.add(1, reason="suspicious")
        assert result["author_id"] == 1

    def test_remove(self, mock_client):
        repo = WatchlistRepository(mock_client)
        repo.remove(1)
        mock_client.table.return_value.update.assert_called_once()

    def test_get_active(self, mock_client):
        set_execute_data(mock_client, [{"author_id": 1}, {"author_id": 2}])
        repo = WatchlistRepository(mock_client)
        result = repo.get_active()
        assert len(result) == 2
