"""Tests for Neo4jEngine (mock-based)."""

from unittest.mock import MagicMock, patch

from cfd.neo4j.engine import Neo4jEngine


class TestNeo4jEngine:
    def _make_engine(self):
        driver = MagicMock()
        return Neo4jEngine(driver)

    def test_pagerank_returns_float(self):
        engine = self._make_engine()
        with patch.object(engine._queries, "run_pagerank", return_value={1: 0.15, 2: 0.25}):
            assert engine.pagerank(1) == 0.15
            assert engine.pagerank(99) == 0.0

    def test_betweenness_returns_float(self):
        engine = self._make_engine()
        with patch.object(engine._queries, "run_betweenness", return_value={1: 0.3}):
            assert engine.betweenness_centrality(1) == 0.3
            assert engine.betweenness_centrality(99) == 0.0

    def test_eigenvector_delegates_to_pagerank(self):
        engine = self._make_engine()
        with patch.object(engine._queries, "run_pagerank", return_value={1: 0.5}):
            assert engine.eigenvector_centrality(1) == 0.5

    def test_louvain_communities(self):
        engine = self._make_engine()
        with patch.object(engine._queries, "run_louvain", return_value={1: 0, 2: 0, 3: 1}):
            partition = engine.louvain_communities()
            assert partition == {1: 0, 2: 0, 3: 1}

    def test_find_cliques_from_rings(self):
        engine = self._make_engine()
        with patch.object(engine._queries, "find_citation_rings", return_value=[{"ring": [1, 2, 3]}]):
            cliques = engine.find_cliques(min_size=3)
            assert len(cliques) == 1
            assert {1, 2, 3} in cliques

    def test_node_count_returns_zero(self):
        engine = self._make_engine()
        assert engine.node_count() == 0

    def test_graceful_failure(self):
        engine = self._make_engine()
        with patch.object(engine._queries, "run_pagerank", side_effect=Exception("connection error")):
            assert engine.pagerank(1) == 0.0
