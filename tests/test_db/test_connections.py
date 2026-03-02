"""Tests for AuthorConnectionRepository."""

from __future__ import annotations

from unittest.mock import MagicMock

from cfd.db.repositories.connections import AuthorConnectionRepository

from .conftest import set_execute_data


class TestAuthorConnectionRepository:
    def test_upsert(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = AuthorConnectionRepository(mock_client)
        result = repo.upsert({"source_author_id": 1, "target_author_id": 2, "connection_type": "citation"})
        assert result["id"] == 1

    def test_get_by_author(self, mock_client):
        # get_by_author makes TWO queries (outgoing + incoming)
        # We need both execute() calls to return data
        table = mock_client.table.return_value
        result1 = MagicMock()
        result1.data = [{"source_author_id": 1, "target_author_id": 2}]
        result2 = MagicMock()
        result2.data = [{"source_author_id": 3, "target_author_id": 1}]
        table.execute.side_effect = [result1, result2]

        repo = AuthorConnectionRepository(mock_client)
        result = repo.get_by_author(1)
        assert len(result) == 2

    def test_get_connection_map(self, mock_client):
        table = mock_client.table.return_value
        result1 = MagicMock()
        result1.data = [{"source_author_id": 1, "target_author_id": 2, "connection_type": "cit", "strength": 5}]
        result2 = MagicMock()
        result2.data = []
        table.execute.side_effect = [result1, result2]

        repo = AuthorConnectionRepository(mock_client)
        cmap = repo.get_connection_map(1)
        assert 1 in cmap["nodes"]
        assert 2 in cmap["nodes"]
        assert len(cmap["edges"]) == 1
