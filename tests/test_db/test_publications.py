"""Tests for PublicationRepository."""

from __future__ import annotations

from datetime import date

from cfd.data.models import Publication
from cfd.db.repositories.publications import PublicationRepository

from .conftest import set_execute_data


def _pub(work_id="W1"):
    return Publication(
        work_id=work_id, doi="10.1234/test", title="Test",
        publication_date=date(2023, 1, 1), journal="J", citation_count=10,
        references_list=["W0"], source_api="openalex",
    )


class TestPublicationRepository:
    def test_upsert_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = PublicationRepository(mock_client)
        result = repo.upsert_many(1, [_pub("W1"), _pub("W2")])
        assert len(result) == 1
        mock_client.table.return_value.upsert.assert_called_once()

    def test_upsert_many_empty(self, mock_client):
        repo = PublicationRepository(mock_client)
        assert repo.upsert_many(1, []) == []

    def test_get_by_author_id(self, mock_client):
        set_execute_data(mock_client, [{"id": 1, "work_id": "W1"}])
        repo = PublicationRepository(mock_client)
        result = repo.get_by_author_id(1)
        assert len(result) == 1

    def test_get_by_author_id_empty(self, mock_client):
        set_execute_data(mock_client, [])
        repo = PublicationRepository(mock_client)
        assert repo.get_by_author_id(999) == []

    def test_get_count_by_author_id(self, mock_client):
        set_execute_data(mock_client, [], count=42)
        repo = PublicationRepository(mock_client)
        assert repo.get_count_by_author_id(1) == 42
