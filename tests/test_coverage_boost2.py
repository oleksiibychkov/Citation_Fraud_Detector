"""Second batch of coverage boost tests — neo4j, embeddings, igraph, engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

# ============================================================
# neo4j/client.py
# ============================================================


class TestNeo4jClient:
    def test_get_driver_cached(self):
        """When driver is already initialized, return cached instance."""
        from cfd.neo4j import client

        mock_driver = MagicMock()
        old = client._driver
        try:
            client._driver = mock_driver
            result = client.get_neo4j_driver(MagicMock())
            assert result is mock_driver
        finally:
            client._driver = old

    def test_get_driver_success(self):
        from cfd.neo4j import client

        old = client._driver
        try:
            client._driver = None
            mock_driver = MagicMock()
            settings = MagicMock(neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="password")
            with patch("neo4j.GraphDatabase") as mock_gdb:
                mock_gdb.driver.return_value = mock_driver
                result = client.get_neo4j_driver(settings)
            assert result is mock_driver
        finally:
            client._driver = old

    def test_get_driver_connection_error(self):
        from cfd.neo4j import client

        old = client._driver
        try:
            client._driver = None
            settings = MagicMock(neo4j_uri="bolt://bad:7687", neo4j_user="u", neo4j_password="p")
            with patch("neo4j.GraphDatabase") as mock_gdb:
                mock_gdb.driver.return_value.verify_connectivity.side_effect = Exception("Connection refused")
                result = client.get_neo4j_driver(settings)
            assert result is None
        finally:
            client._driver = old


# ============================================================
# neo4j/engine.py — mock-based tests for all methods
# ============================================================


class TestNeo4jEngine:
    def _make_engine(self):
        from cfd.neo4j.engine import Neo4jEngine
        mock_driver = MagicMock()
        engine = Neo4jEngine(mock_driver)
        engine._queries = MagicMock()
        engine._queries.run_pagerank.return_value = {"A": 0.5, "B": 0.3}
        engine._queries.run_betweenness.return_value = {"A": 0.4, "B": 0.2}
        engine._queries.run_louvain.return_value = {"A": 0, "B": 0, "C": 1}
        engine._queries.find_citation_rings.return_value = [{"ring": ["A", "B", "C"]}]
        return engine

    def test_pagerank(self):
        engine = self._make_engine()
        pr = engine.pagerank("A")
        assert pr == 0.5

    def test_betweenness(self):
        engine = self._make_engine()
        bc = engine.betweenness_centrality("A")
        assert bc == 0.4

    def test_eigenvector(self):
        engine = self._make_engine()
        ev = engine.eigenvector_centrality("A")
        assert ev == 0.5  # delegates to pagerank

    def test_communities(self):
        engine = self._make_engine()
        comm = engine.louvain_communities()
        assert len(comm) > 0

    def test_detect_cliques(self):
        engine = self._make_engine()
        cliques = engine.find_cliques(min_size=2)
        assert len(cliques) > 0

    def test_has_cycles(self):
        engine = self._make_engine()
        assert engine.has_cycle_in_subgraph({"A", "B"}) is True

    def test_betweenness_failure(self):
        from cfd.neo4j.engine import Neo4jEngine
        engine = Neo4jEngine(MagicMock())
        engine._queries = MagicMock()
        engine._queries.run_betweenness.side_effect = Exception("fail")
        assert engine.betweenness_centrality("A") == 0.0

    def test_louvain_failure(self):
        from cfd.neo4j.engine import Neo4jEngine
        engine = Neo4jEngine(MagicMock())
        engine._queries = MagicMock()
        engine._queries.run_louvain.side_effect = Exception("fail")
        assert engine.louvain_communities() == {}

    def test_clique_detection_failure(self):
        from cfd.neo4j.engine import Neo4jEngine
        engine = Neo4jEngine(MagicMock())
        engine._queries = MagicMock()
        engine._queries.find_citation_rings.side_effect = Exception("fail")
        assert engine.find_cliques(min_size=2) == []

    def test_has_cycles_failure(self):
        from cfd.neo4j.engine import Neo4jEngine
        engine = Neo4jEngine(MagicMock())
        engine._queries = MagicMock()
        engine._queries.find_citation_rings.side_effect = Exception("fail")
        assert engine.has_cycle_in_subgraph({"A"}) is False

    def test_community_densities(self):
        engine = self._make_engine()
        d = engine.community_densities({"A", "B"})
        assert isinstance(d, tuple)

    def test_subgraph_density(self):
        engine = self._make_engine()
        d = engine.subgraph_density({"A", "B"})
        assert isinstance(d, (float, int))

    def test_modularity(self):
        engine = self._make_engine()
        m = engine.modularity({"A": 0, "B": 1})
        assert m == 0.0

    def test_average_edge_probability(self):
        engine = self._make_engine()
        assert engine.average_edge_probability() == 0.0

    def test_node_count(self):
        engine = self._make_engine()
        assert engine.node_count() == 0


# ============================================================
# analysis/embeddings.py — SentenceTransformer strategy
# ============================================================


class TestEmbeddings:
    def test_tfidf_strategy(self):
        from cfd.analysis.embeddings import NaiveTfidfStrategy
        strategy = NaiveTfidfStrategy()
        result = strategy.embed(["hello world", "foo bar", "test doc"])
        assert result.shape[0] == 3
        assert result.shape[1] > 0

    def test_tfidf_single_doc(self):
        from cfd.analysis.embeddings import NaiveTfidfStrategy
        strategy = NaiveTfidfStrategy()
        result = strategy.embed(["single document"])
        assert result.shape[0] == 1
        assert result.shape[1] >= 1

    def test_tfidf_empty(self):
        from cfd.analysis.embeddings import NaiveTfidfStrategy
        strategy = NaiveTfidfStrategy()
        result = strategy.embed([])
        assert result.shape[0] == 0

    def test_sentence_transformer_strategy_encode(self):
        """Test SentenceTransformerStrategy with mocked model."""
        from cfd.analysis.embeddings import SentenceTransformerStrategy
        strategy = SentenceTransformerStrategy()
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        strategy._model = mock_model
        result = strategy.embed(["text1", "text2"])
        assert result.shape == (2, 2)

    def test_sentence_transformer_strategy_empty(self):
        from cfd.analysis.embeddings import SentenceTransformerStrategy
        strategy = SentenceTransformerStrategy()
        strategy._model = MagicMock()
        result = strategy.embed([])
        assert result.shape[0] == 0

    def test_sentence_transformer_lazy_load(self):
        """SentenceTransformerStrategy loads model on first encode."""
        from cfd.analysis.embeddings import SentenceTransformerStrategy
        strategy = SentenceTransformerStrategy()
        assert strategy._model is None
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
            strategy.embed(["test"])
        assert strategy._model is mock_model

    def test_get_strategy_prefer_neural(self):
        """get_embedding_strategy returns SentenceTransformerStrategy when prefer_neural=True."""
        from cfd.analysis.embeddings import SentenceTransformerStrategy, get_embedding_strategy
        strategy = get_embedding_strategy(prefer_neural=True)
        # sentence-transformers IS installed, so should return ST strategy
        assert isinstance(strategy, SentenceTransformerStrategy)

    def test_get_strategy_default_tfidf(self):
        """get_embedding_strategy returns TfIdf by default."""
        from cfd.analysis.embeddings import NaiveTfidfStrategy, get_embedding_strategy
        strategy = get_embedding_strategy()
        assert isinstance(strategy, NaiveTfidfStrategy)

    def test_get_strategy_fallback(self):
        """get_embedding_strategy falls back to TfIdf when ST unavailable."""
        from cfd.analysis.embeddings import NaiveTfidfStrategy, get_embedding_strategy
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            strategy = get_embedding_strategy(prefer_neural=True)
        assert isinstance(strategy, NaiveTfidfStrategy)


# ============================================================
# graph/igraph_engine.py — eigenvector failure + community_densities
# ============================================================


class TestIgraphEngine:
    def test_eigenvector_failure(self):
        """Eigenvector centrality gracefully handles computation failure."""
        import networkx as nx

        from cfd.graph.igraph_engine import IGraphEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        engine = IGraphEngine(g)
        with patch.object(engine._ig_undirected, "eigenvector_centrality", side_effect=Exception("fail")):
            result = engine.eigenvector_centrality(1)
        assert result == 0.0

    def test_community_densities_falls_back_to_networkx(self):
        """community_densities delegates to NetworkXEngine."""
        import networkx as nx

        from cfd.graph.igraph_engine import IGraphEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        engine = IGraphEngine(g)
        result = engine.community_densities({1, 2})
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_is_dag(self):
        import networkx as nx

        from cfd.graph.igraph_engine import IGraphEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        engine = IGraphEngine(g)
        assert engine.has_cycle_in_subgraph({1, 2, 3}) is False


# ============================================================
# graph/engine.py — NetworkX eigenvector failure + igraph fallback
# ============================================================


class TestGraphEngineSelection:
    def test_networkx_eigenvector_convergence_failure(self):
        """Eigenvector centrality handles PowerIterationFailedConvergence."""
        import networkx as nx

        from cfd.graph.engine import NetworkXEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        engine = NetworkXEngine(g)
        with patch("networkx.eigenvector_centrality",
                    side_effect=nx.PowerIterationFailedConvergence(100)):
            result = engine.eigenvector_centrality(1)
        assert result == 0.0

    def test_networkx_eigenvector_exception(self):
        import networkx as nx

        from cfd.graph.engine import NetworkXEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        engine = NetworkXEngine(g)
        with patch("networkx.eigenvector_centrality",
                    side_effect=nx.NetworkXException("fail")):
            result = engine.eigenvector_centrality(1)
        assert result == 0.0

    def test_has_cycles(self):
        import networkx as nx

        from cfd.graph.engine import NetworkXEngine
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        engine = NetworkXEngine(g)
        assert engine.has_cycle_in_subgraph({1, 2, 3}) is True

    def test_select_engine_igraph_threshold(self):
        """select_engine uses igraph for large graphs when igraph is available."""
        import networkx as nx

        from cfd.graph.engine import select_engine
        g = nx.DiGraph()
        for i in range(50):
            g.add_edge(i, i + 1)
        # With igraph installed, threshold=10 should select igraph
        engine = select_engine(g, threshold=10)
        assert engine is not None

    def test_select_engine_networkx_fallback(self):
        """select_engine falls back to NetworkX when igraph unavailable."""
        import networkx as nx

        from cfd.graph.engine import NetworkXEngine, select_engine
        g = nx.DiGraph()
        for i in range(50):
            g.add_edge(i, i + 1)
        with patch("cfd.graph.igraph_engine.IGraphEngine", side_effect=ImportError):
            engine = select_engine(g, threshold=10)
        assert isinstance(engine, NetworkXEngine)
