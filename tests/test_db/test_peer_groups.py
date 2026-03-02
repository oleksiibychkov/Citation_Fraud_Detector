"""Tests for PeerGroupRepository."""

from unittest.mock import MagicMock

from cfd.db.repositories.peer_groups import PeerGroupRepository


def _mock_chain(client, *attrs):
    """Build a chained mock return value."""
    obj = client.table.return_value
    for attr in attrs:
        obj = getattr(obj, attr).return_value
    return obj


class TestPeerGroupRepository:
    def test_save(self):
        client = MagicMock()
        client.table.return_value.upsert.return_value.execute.return_value.data = [{"id": 1}]
        repo = PeerGroupRepository(client)
        result = repo.save(author_id=1, peer_author_ids=[2, 3], discipline="CS")
        assert result == {"id": 1}

    def test_get_by_author_id(self):
        client = MagicMock()
        chain = _mock_chain(client, "select", "eq", "order", "limit")
        chain.execute.return_value.data = [{"author_id": 1, "peer_author_ids": [2, 3]}]
        repo = PeerGroupRepository(client)
        result = repo.get_by_author_id(1)
        assert result is not None
        assert result["author_id"] == 1

    def test_get_by_author_id_not_found(self):
        client = MagicMock()
        chain = _mock_chain(client, "select", "eq", "order", "limit")
        chain.execute.return_value.data = []
        repo = PeerGroupRepository(client)
        result = repo.get_by_author_id(999)
        assert result is None

    def test_find_peers(self):
        client = MagicMock()
        chain = _mock_chain(client, "select", "eq", "gte", "lte", "limit")
        chain.execute.return_value.data = [
            {"id": 1, "discipline": "CS", "h_index": 10},
            {"id": 2, "discipline": "CS", "h_index": 12},
        ]
        repo = PeerGroupRepository(client)
        result = repo.find_peers(discipline="CS", min_pubs=5, max_pubs=50)
        assert len(result) == 2

    def test_find_peers_empty(self):
        client = MagicMock()
        chain = _mock_chain(client, "select", "eq", "gte", "lte", "limit")
        chain.execute.return_value.data = []
        repo = PeerGroupRepository(client)
        result = repo.find_peers(discipline="Rare Field")
        assert result == []
