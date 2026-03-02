"""Tests for TheoremResultRepository."""

from __future__ import annotations

from cfd.db.repositories.theorem_results import TheoremResultRepository

from .conftest import set_execute_data


class TestTheoremResultRepository:
    def test_save_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = TheoremResultRepository(mock_client)
        results = [{"theorem_number": 1, "passed": True, "details": {}}]
        result = repo.save_many(1, results, "5.0.0")
        assert len(result) == 1

    def test_save_many_empty(self, mock_client):
        repo = TheoremResultRepository(mock_client)
        assert repo.save_many(1, []) == []

    def test_get_by_author_id(self, mock_client):
        set_execute_data(mock_client, [{"theorem_number": 1, "passed": True}])
        repo = TheoremResultRepository(mock_client)
        result = repo.get_by_author_id(1)
        assert len(result) == 1
