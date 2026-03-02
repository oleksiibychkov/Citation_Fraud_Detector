"""Tests for CliqueRepository."""

from __future__ import annotations

from cfd.db.repositories.cliques import CliqueRepository

from .conftest import set_execute_data


class TestCliqueRepository:
    def test_save_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = CliqueRepository(mock_client)
        result = repo.save_many([{"members": [1, 2, 3], "severity": "moderate"}])
        assert len(result) == 1

    def test_save_many_empty(self, mock_client):
        repo = CliqueRepository(mock_client)
        assert repo.save_many([]) == []

    def test_get_by_severity_filtered(self, mock_client):
        set_execute_data(mock_client, [{"severity": "high"}])
        repo = CliqueRepository(mock_client)
        result = repo.get_by_severity("high")
        assert len(result) == 1

    def test_get_by_severity_all(self, mock_client):
        set_execute_data(mock_client, [{"severity": "high"}, {"severity": "low"}])
        repo = CliqueRepository(mock_client)
        result = repo.get_by_severity()
        assert len(result) == 2
