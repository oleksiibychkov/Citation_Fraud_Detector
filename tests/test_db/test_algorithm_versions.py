"""Tests for AlgorithmVersionRepository."""

from __future__ import annotations

from cfd.db.repositories.algorithm_versions import AlgorithmVersionRepository

from .conftest import set_execute_data


class TestAlgorithmVersionRepository:
    def test_get_by_version_found(self, mock_client):
        set_execute_data(mock_client, [{"version": "5.0.0", "indicator_count": 20}])
        repo = AlgorithmVersionRepository(mock_client)
        result = repo.get_by_version("5.0.0")
        assert result is not None
        assert result["version"] == "5.0.0"

    def test_get_by_version_not_found(self, mock_client):
        set_execute_data(mock_client, [])
        repo = AlgorithmVersionRepository(mock_client)
        assert repo.get_by_version("99.0.0") is None

    def test_get_all(self, mock_client):
        set_execute_data(mock_client, [{"version": "5.0.0"}, {"version": "4.0.0"}])
        repo = AlgorithmVersionRepository(mock_client)
        result = repo.get_all()
        assert len(result) == 2

    def test_register(self, mock_client):
        set_execute_data(mock_client, [{"version": "6.0.0"}])
        repo = AlgorithmVersionRepository(mock_client)
        result = repo.register({"version": "6.0.0", "indicator_count": 25})
        assert result["version"] == "6.0.0"
