"""Tests for Peer Benchmark (PB) indicator."""

from unittest.mock import MagicMock

from cfd.analysis.peer_benchmark import _compute_peer_deviation, compute_pb
from cfd.data.models import AuthorData, AuthorProfile


def _make_profile(**kw):
    defaults = {"surname": "Test", "source_api": "openalex", "discipline": "Computer Science"}
    defaults.update(kw)
    return AuthorProfile(**defaults)


class TestComputePB:
    def test_no_repos(self):
        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_pb(ad)
        assert result.indicator_type == "PB"
        assert result.value == 0.0
        assert result.details["status"] == "no_db_connection"

    def test_insufficient_peers(self):
        peer_repo = MagicMock()
        author_repo = MagicMock()
        peer_repo.find_peers.return_value = [{"id": 1, "h_index": 10, "citation_count": 100, "publication_count": 20}]

        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_pb(ad, peer_repo=peer_repo, author_repo=author_repo, min_peers=3)
        assert result.value == 0.0
        assert result.details["status"] == "insufficient_peers"

    def test_author_at_peer_median(self):
        peer_repo = MagicMock()
        author_repo = MagicMock()
        peers = [
            {"id": i, "h_index": 10, "citation_count": 200, "publication_count": 20}
            for i in range(5)
        ]
        peer_repo.find_peers.return_value = peers

        ad = AuthorData(profile=_make_profile(h_index=10, publication_count=20, citation_count=200))
        result = compute_pb(ad, peer_repo=peer_repo, author_repo=author_repo)
        # Author matches peers exactly → z-scores = 0 → PB = 0
        assert result.value == 0.0

    def test_author_far_above_peers(self):
        peer_repo = MagicMock()
        author_repo = MagicMock()
        peers = [
            {"id": i, "h_index": 5 + i, "citation_count": 50 + i * 10, "publication_count": 10 + i}
            for i in range(5)
        ]
        peer_repo.find_peers.return_value = peers

        ad = AuthorData(profile=_make_profile(h_index=50, publication_count=100, citation_count=5000))
        result = compute_pb(ad, peer_repo=peer_repo, author_repo=author_repo)
        assert result.value > 0.0

    def test_no_discipline(self):
        peer_repo = MagicMock()
        author_repo = MagicMock()
        peer_repo.find_peers.return_value = []

        ad = AuthorData(profile=_make_profile(discipline=None, h_index=10, publication_count=20, citation_count=200))
        result = compute_pb(ad, peer_repo=peer_repo, author_repo=author_repo)
        assert result.value == 0.0

    def test_details_fields(self):
        peer_repo = MagicMock()
        author_repo = MagicMock()
        peers = [
            {"id": i, "h_index": 8 + i, "citation_count": 100 + i * 10, "publication_count": 15 + i}
            for i in range(5)
        ]
        peer_repo.find_peers.return_value = peers

        ad = AuthorData(profile=_make_profile(h_index=20, publication_count=30, citation_count=500))
        result = compute_pb(ad, peer_repo=peer_repo, author_repo=author_repo)
        assert "peer_count" in result.details
        assert "deviations" in result.details
        assert "author_metrics" in result.details

    def test_value_normalized(self):
        peer_repo = MagicMock()
        author_repo = MagicMock()
        peers = [{"id": i, "h_index": 5, "citation_count": 50, "publication_count": 10} for i in range(5)]
        peer_repo.find_peers.return_value = peers

        ad = AuthorData(profile=_make_profile(h_index=100, publication_count=500, citation_count=50000))
        result = compute_pb(ad, peer_repo=peer_repo, author_repo=author_repo)
        assert 0.0 <= result.value <= 1.0


class TestComputePeerDeviation:
    def test_identical_metrics(self):
        author = {"h_index": 10, "citation_count": 100, "publication_count": 20}
        peers = [{"h_index": 10, "citation_count": 100, "publication_count": 20}] * 5
        devs = _compute_peer_deviation(author, peers)
        for _metric, d in devs.items():
            assert d["z_score"] == 0.0

    def test_above_median(self):
        author = {"h_index": 50, "citation_count": 100, "publication_count": 20}
        peers = [{"h_index": 10, "citation_count": 100, "publication_count": 20}] * 5
        devs = _compute_peer_deviation(author, peers)
        assert devs["h_index"]["z_score"] is not None

    def test_empty_peers(self):
        author = {"h_index": 10, "citation_count": 100, "publication_count": 20}
        devs = _compute_peer_deviation(author, [])
        for _metric, d in devs.items():
            assert d["z_score"] is None
