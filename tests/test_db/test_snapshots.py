"""Tests for SnapshotRepository."""

from __future__ import annotations

from cfd.db.repositories.snapshots import SnapshotRepository

from .conftest import set_execute_data


class TestSnapshotRepository:
    def test_save(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = SnapshotRepository(mock_client)
        result = repo.save({"author_id": 1, "fraud_score": 0.42})
        assert result["id"] == 1

    def test_get_by_author_id(self, mock_client):
        set_execute_data(mock_client, [{"fraud_score": 0.42}])
        repo = SnapshotRepository(mock_client)
        result = repo.get_by_author_id(1)
        assert len(result) == 1

    def test_get_by_author_id_empty(self, mock_client):
        set_execute_data(mock_client, [])
        repo = SnapshotRepository(mock_client)
        assert repo.get_by_author_id(999) == []
