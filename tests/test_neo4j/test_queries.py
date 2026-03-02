"""Tests for Neo4jQueries."""

from __future__ import annotations

from unittest.mock import MagicMock

from cfd.neo4j.queries import Neo4jQueries


def _make_queries(records=None):
    """Create Neo4jQueries with a mocked driver and session."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)

    if records is not None:
        session.run.return_value = records
    else:
        session.run.return_value = []

    return Neo4jQueries(driver), session


class TestFindCitationRings:
    def test_returns_results(self):
        mock_records = [{"ring": [1, 2, 3, 1]}]
        queries, _session = _make_queries(mock_records)
        result = queries.find_citation_rings(min_length=3)
        assert len(result) == 1
        assert result[0]["ring"] == [1, 2, 3, 1]

    def test_empty_results(self):
        queries, _session = _make_queries([])
        result = queries.find_citation_rings()
        assert result == []


class TestFindMutualCitations:
    def test_returns_pairs(self):
        mock_records = [{"author_a": 1, "author_b": 2, "mcr": 0.8}]
        queries, _session = _make_queries(mock_records)
        result = queries.find_mutual_citations(threshold=0.3)
        assert len(result) == 1
        assert result[0]["mcr"] == 0.8

    def test_empty(self):
        queries, _session = _make_queries([])
        result = queries.find_mutual_citations()
        assert result == []


class TestRunLouvain:
    def test_returns_partition(self):
        mock_records = [
            {"author_id": 1, "communityId": 0},
            {"author_id": 2, "communityId": 0},
            {"author_id": 3, "communityId": 1},
        ]
        queries, session = _make_queries()
        # First call: exists check, second: project (maybe), third: louvain
        # _ensure_graph_projection does 1-2 calls, then run_louvain does 1 call
        # session.run is called for exists check, then for louvain query
        exists_result = MagicMock()
        exists_result.single.return_value = {"exists": True}
        session.run.side_effect = [exists_result, mock_records]

        result = queries.run_louvain()
        assert result == {1: 0, 2: 0, 3: 1}


class TestRunPagerank:
    def test_returns_scores(self):
        mock_records = [
            {"author_id": 1, "score": 0.5},
            {"author_id": 2, "score": 0.3},
        ]
        queries, session = _make_queries()
        exists_result = MagicMock()
        exists_result.single.return_value = {"exists": True}
        session.run.side_effect = [exists_result, mock_records]

        result = queries.run_pagerank()
        assert result == {1: 0.5, 2: 0.3}


class TestRunBetweenness:
    def test_returns_scores(self):
        mock_records = [{"author_id": 1, "score": 0.9}]
        queries, session = _make_queries()
        exists_result = MagicMock()
        exists_result.single.return_value = {"exists": True}
        session.run.side_effect = [exists_result, mock_records]

        result = queries.run_betweenness()
        assert result == {1: 0.9}


class TestEnsureGraphProjection:
    def test_creates_projection_when_missing(self):
        queries, session = _make_queries()
        exists_result = MagicMock()
        exists_result.single.return_value = {"exists": False}
        session.run.side_effect = [exists_result, None]

        queries._ensure_graph_projection("cfd_graph")
        assert session.run.call_count == 2

    def test_skips_when_exists(self):
        queries, session = _make_queries()
        exists_result = MagicMock()
        exists_result.single.return_value = {"exists": True}
        session.run.return_value = exists_result

        queries._ensure_graph_projection("cfd_graph")
        assert session.run.call_count == 1
