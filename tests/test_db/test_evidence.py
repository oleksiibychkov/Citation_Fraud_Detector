"""Tests for ReportEvidenceRepository."""

from __future__ import annotations

from cfd.db.repositories.evidence import ReportEvidenceRepository

from .conftest import set_execute_data


class TestReportEvidenceRepository:
    def test_save_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = ReportEvidenceRepository(mock_client)
        evidence = [{"indicator_type": "SCR", "value": 0.6, "description": "High self-citation"}]
        result = repo.save_many(1, evidence, "5.0.0")
        assert len(result) == 1

    def test_save_many_empty(self, mock_client):
        repo = ReportEvidenceRepository(mock_client)
        assert repo.save_many(1, [], "5.0.0") == []

    def test_get_by_author(self, mock_client):
        set_execute_data(mock_client, [{"indicator_type": "SCR"}])
        repo = ReportEvidenceRepository(mock_client)
        result = repo.get_by_author(1)
        assert len(result) == 1
