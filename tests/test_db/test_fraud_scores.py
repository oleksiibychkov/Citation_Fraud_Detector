"""Tests for FraudScoreRepository."""

from __future__ import annotations

from cfd.db.repositories.fraud_scores import FraudScoreRepository

from .conftest import set_execute_data


class TestFraudScoreRepository:
    def test_save(self, mock_client):
        set_execute_data(mock_client, [{"id": 1, "score": 0.42}])
        repo = FraudScoreRepository(mock_client)
        result = repo.save(
            author_id=1, score=0.42, confidence_level="moderate",
            indicator_weights={"SCR": 0.08}, indicator_values={"SCR": 0.6},
            triggered_indicators=["SCR"], algorithm_version="5.0.0",
        )
        assert result["score"] == 0.42

    def test_save_empty_result(self, mock_client):
        set_execute_data(mock_client, [])
        repo = FraudScoreRepository(mock_client)
        result = repo.save(1, 0.1, "normal", {}, {}, [])
        assert result["score"] == 0.1

    def test_get_latest_by_author_found(self, mock_client):
        set_execute_data(mock_client, [{"id": 1, "score": 0.5}])
        repo = FraudScoreRepository(mock_client)
        result = repo.get_latest_by_author(1)
        assert result is not None
        assert result["score"] == 0.5

    def test_get_latest_by_author_not_found(self, mock_client):
        set_execute_data(mock_client, [])
        repo = FraudScoreRepository(mock_client)
        assert repo.get_latest_by_author(999) is None

    def test_get_all_ranked(self, mock_client):
        set_execute_data(mock_client, [
            {"author_id": 1, "score": 0.9, "calculated_at": "2026-01-02"},
            {"author_id": 2, "score": 0.5, "calculated_at": "2026-01-01"},
        ])
        repo = FraudScoreRepository(mock_client)
        result = repo.get_all_ranked(limit=10)
        assert len(result) == 2
        assert result[0]["score"] == 0.9

    def test_get_all_ranked_deduplicates(self, mock_client):
        set_execute_data(mock_client, [
            {"author_id": 1, "score": 0.9, "calculated_at": "2026-01-02"},
            {"author_id": 1, "score": 0.5, "calculated_at": "2026-01-01"},
        ])
        repo = FraudScoreRepository(mock_client)
        result = repo.get_all_ranked(limit=10)
        assert len(result) == 1
        assert result[0]["score"] == 0.9
