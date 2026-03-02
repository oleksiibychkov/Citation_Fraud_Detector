"""Tests for CommunityRepository."""

from __future__ import annotations

from cfd.db.repositories.communities import CommunityRepository

from .conftest import set_execute_data


class TestCommunityRepository:
    def test_save_many(self, mock_client):
        set_execute_data(mock_client, [{"id": 1}])
        repo = CommunityRepository(mock_client)
        result = repo.save_many([{"author_id": 1, "community_id": 0}])
        assert len(result) == 1

    def test_save_many_empty(self, mock_client):
        repo = CommunityRepository(mock_client)
        assert repo.save_many([]) == []

    def test_get_by_author_id(self, mock_client):
        set_execute_data(mock_client, [{"community_id": 0}])
        repo = CommunityRepository(mock_client)
        result = repo.get_by_author_id(1)
        assert len(result) == 1
