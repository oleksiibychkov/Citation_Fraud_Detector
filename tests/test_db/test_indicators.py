"""Tests for IndicatorRepository."""

from __future__ import annotations

from cfd.db.repositories.indicators import IndicatorRepository

from .conftest import set_execute_data


class TestIndicatorRepository:
    def test_save_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = IndicatorRepository(mock_client)
        inds = [{"indicator_type": "SCR", "value": 0.6, "details": {}}]
        result = repo.save_many(1, inds, "5.0.0")
        assert len(result) == 1
        mock_client.table.return_value.insert.assert_called_once()

    def test_save_many_empty(self, mock_client):
        repo = IndicatorRepository(mock_client)
        assert repo.save_many(1, []) == []

    def test_get_by_author_id(self, mock_client):
        set_execute_data(mock_client, [{"indicator_type": "SCR", "value": 0.6}])
        repo = IndicatorRepository(mock_client)
        result = repo.get_by_author_id(1)
        assert len(result) == 1
        assert result[0]["indicator_type"] == "SCR"
