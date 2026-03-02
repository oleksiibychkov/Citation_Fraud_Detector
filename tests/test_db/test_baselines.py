"""Tests for DisciplineBaselineRepository."""

from __future__ import annotations

from cfd.db.repositories.baselines import DisciplineBaselineRepository

from .conftest import set_execute_data


class TestDisciplineBaselineRepository:
    def test_get_by_discipline_found(self, mock_client):
        set_execute_data(mock_client, [{"discipline": "CS", "avg_scr": 0.15}])
        repo = DisciplineBaselineRepository(mock_client)
        result = repo.get_by_discipline("CS")
        assert result is not None
        assert result["discipline"] == "CS"

    def test_get_by_discipline_not_found(self, mock_client):
        set_execute_data(mock_client, [])
        repo = DisciplineBaselineRepository(mock_client)
        assert repo.get_by_discipline("Unknown") is None

    def test_get_all(self, mock_client):
        set_execute_data(mock_client, [{"discipline": "CS"}, {"discipline": "Physics"}])
        repo = DisciplineBaselineRepository(mock_client)
        assert len(repo.get_all()) == 2

    def test_upsert(self, mock_client):
        set_execute_data(mock_client, [{"discipline": "CS"}])
        repo = DisciplineBaselineRepository(mock_client)
        result = repo.upsert({"discipline": "CS", "avg_scr": 0.12})
        assert result["discipline"] == "CS"
