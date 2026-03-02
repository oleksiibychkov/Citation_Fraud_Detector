"""Tests for AuthorRepository."""

from __future__ import annotations

from cfd.data.models import AuthorProfile
from cfd.db.repositories.authors import AuthorRepository

from .conftest import set_execute_data


def _profile(**overrides) -> AuthorProfile:
    defaults = dict(
        scopus_id="57200000001", orcid="0000-0002-1234-5678", openalex_id="A123",
        surname="Ivanenko", full_name="Oleksandr Ivanenko",
        display_name_variants=[], institution="Kyiv U", discipline="CS",
        h_index=15, publication_count=50, citation_count=500, source_api="openalex",
    )
    defaults.update(overrides)
    return AuthorProfile(**defaults)


class TestAuthorRepository:
    def test_upsert_with_scopus_id(self, mock_client):
        set_execute_data(mock_client, [{"id": 1, "surname": "Ivanenko"}])
        repo = AuthorRepository(mock_client)
        result = repo.upsert(_profile())
        assert result["id"] == 1
        mock_client.table.return_value.upsert.assert_called_once()

    def test_upsert_with_orcid_only(self, mock_client):
        set_execute_data(mock_client, [{"id": 2}])
        repo = AuthorRepository(mock_client)
        result = repo.upsert(_profile(scopus_id=None))
        assert result["id"] == 2

    def test_upsert_insert_fallback(self, mock_client):
        set_execute_data(mock_client, [{"id": 3}])
        repo = AuthorRepository(mock_client)
        result = repo.upsert(_profile(scopus_id=None, orcid=None))
        assert result["id"] == 3
        mock_client.table.return_value.insert.assert_called_once()

    def test_upsert_empty_result(self, mock_client):
        set_execute_data(mock_client, [])
        repo = AuthorRepository(mock_client)
        result = repo.upsert(_profile())
        assert result["surname"] == "Ivanenko"

    def test_get_by_scopus_id_found(self, mock_client):
        set_execute_data(mock_client, [{"id": 1, "scopus_id": "57200000001"}])
        repo = AuthorRepository(mock_client)
        result = repo.get_by_scopus_id("57200000001")
        assert result is not None
        assert result["scopus_id"] == "57200000001"

    def test_get_by_scopus_id_not_found(self, mock_client):
        set_execute_data(mock_client, [])
        repo = AuthorRepository(mock_client)
        assert repo.get_by_scopus_id("000") is None

    def test_get_by_orcid_found(self, mock_client):
        set_execute_data(mock_client, [{"id": 1, "orcid": "0000-0002-1234-5678"}])
        repo = AuthorRepository(mock_client)
        result = repo.get_by_orcid("0000-0002-1234-5678")
        assert result is not None

    def test_get_by_id_found(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = AuthorRepository(mock_client)
        assert repo.get_by_id(1) is not None

    def test_get_by_id_not_found(self, mock_client):
        set_execute_data(mock_client, [])
        repo = AuthorRepository(mock_client)
        assert repo.get_by_id(999) is None
