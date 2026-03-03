"""Tests for CitationRepository."""

from __future__ import annotations

from datetime import date

from cfd.data.models import Citation
from cfd.db.repositories.citations import CitationRepository

from .conftest import set_execute_data


def _cit(src="W1", tgt="W2"):
    return Citation(
        source_work_id=src, target_work_id=tgt,
        source_author_id="1", target_author_id="2",
        citation_date=date(2023, 6, 1), is_self_citation=False,
        source_api="openalex",
    )


class TestCitationRepository:
    def test_upsert_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = CitationRepository(mock_client)
        result = repo.upsert_many([_cit()], target_author_id="2")
        assert len(result) == 1

    def test_upsert_many_empty(self, mock_client):
        repo = CitationRepository(mock_client)
        assert repo.upsert_many([]) == []

    def test_upsert_many_chunked(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = CitationRepository(mock_client)
        cits = [_cit(f"W{i}", f"W{i+1}") for i in range(600)]
        repo.upsert_many(cits)
        # Should be called twice: 500 + 100
        assert mock_client.table.return_value.upsert.call_count == 2

    def test_get_by_target_author(self, mock_client):
        set_execute_data(mock_client, [{"source_work_id": "W1"}])
        repo = CitationRepository(mock_client)
        assert len(repo.get_by_target_author(1)) == 1

    def test_get_by_source_author(self, mock_client):
        set_execute_data(mock_client, [{"source_work_id": "W1"}])
        repo = CitationRepository(mock_client)
        assert len(repo.get_by_source_author(1)) == 1
