"""Tests for GraphEngine abstraction and NetworkXEngine implementation."""

import networkx as nx
import pytest

from cfd.graph.engine import GraphEngine, NetworkXEngine, select_engine


@pytest.fixture
def simple_graph():
    """Small directed graph for testing."""
    g = nx.DiGraph()
    g.add_weighted_edges_from([
        (1, 2, 1.0), (2, 1, 1.0),
        (2, 3, 1.0), (3, 2, 1.0),
        (3, 1, 1.0), (1, 3, 1.0),
        (4, 1, 1.0), (4, 2, 1.0),
    ])
    return g


@pytest.fixture
def triangle_undirected():
    """Undirected triangle graph (clique of size 3)."""
    g = nx.Graph()
    g.add_weighted_edges_from([
        (1, 2, 1.0), (2, 3, 1.0), (1, 3, 1.0),
    ])
    return g


@pytest.fixture
def engine(simple_graph):
    return NetworkXEngine(simple_graph)


@pytest.fixture
def undirected_engine(triangle_undirected):
    return NetworkXEngine(triangle_undirected)


class TestNetworkXEngineBasics:
    def test_node_count(self, engine):
        assert engine.node_count() == 4

    def test_node_count_undirected(self, undirected_engine):
        assert undirected_engine.node_count() == 3


class TestCentrality:
    def test_eigenvector_centrality_returns_float(self, engine):
        val = engine.eigenvector_centrality(1)
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    def test_eigenvector_missing_node(self, engine):
        val = engine.eigenvector_centrality(999)
        assert val == 0.0

    def test_betweenness_centrality_returns_float(self, engine):
        val = engine.betweenness_centrality(1)
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    def test_betweenness_missing_node(self, engine):
        val = engine.betweenness_centrality(999)
        assert val == 0.0

    def test_pagerank_returns_float(self, engine):
        val = engine.pagerank(1)
        assert isinstance(val, float)
        assert val > 0.0

    def test_pagerank_missing_node(self, engine):
        val = engine.pagerank(999)
        assert val == 0.0

    def test_centrality_caching(self, engine):
        """Calling twice should use cached values."""
        v1 = engine.eigenvector_centrality(1)
        v2 = engine.eigenvector_centrality(1)
        assert v1 == v2
        assert engine._eigen_cache is not None


class TestCommunities:
    def test_louvain_returns_partition(self, engine):
        partition = engine.louvain_communities()
        assert isinstance(partition, dict)
        assert set(partition.keys()) == {1, 2, 3, 4}
        for cid in partition.values():
            assert isinstance(cid, int)

    def test_modularity_returns_float(self, engine):
        partition = engine.louvain_communities()
        mod = engine.modularity(partition)
        assert isinstance(mod, float)
        assert -0.5 <= mod <= 1.0


class TestCliques:
    def test_find_cliques_triangle(self, undirected_engine):
        cliques = undirected_engine.find_cliques(min_size=3)
        assert len(cliques) >= 1
        assert any(len(c) == 3 for c in cliques)

    def test_find_cliques_no_result(self):
        g = nx.Graph()
        g.add_edge(1, 2, weight=1.0)
        eng = NetworkXEngine(g)
        cliques = eng.find_cliques(min_size=3)
        assert cliques == []


class TestCycles:
    def test_has_cycle_directed(self, engine):
        assert engine.has_cycle_in_subgraph({1, 2, 3}) is True

    def test_no_cycle_acyclic(self):
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        eng = NetworkXEngine(g)
        assert eng.has_cycle_in_subgraph({1, 2, 3}) is False


class TestDensity:
    def test_community_densities(self, undirected_engine):
        internal, external = undirected_engine.community_densities({1, 2})
        assert isinstance(internal, float)
        assert isinstance(external, float)
        assert 0.0 <= internal <= 1.0

    def test_subgraph_density_complete(self, undirected_engine):
        density = undirected_engine.subgraph_density({1, 2, 3})
        assert density == 1.0  # complete triangle

    def test_average_edge_probability(self, undirected_engine):
        p = undirected_engine.average_edge_probability()
        assert isinstance(p, float)
        assert 0.0 < p <= 1.0

    def test_average_edge_probability_empty(self):
        g = nx.Graph()
        g.add_node(1)
        eng = NetworkXEngine(g)
        assert eng.average_edge_probability() == 0.0


class TestSelectEngine:
    def test_select_returns_networkx_for_small(self, simple_graph):
        eng = select_engine(simple_graph)
        assert isinstance(eng, NetworkXEngine)

    def test_select_returns_networkx_when_igraph_missing(self, simple_graph):
        eng = select_engine(simple_graph, threshold=1)
        assert isinstance(eng, (NetworkXEngine, GraphEngine))


class TestEdgeCases:
    def test_empty_graph(self):
        g = nx.DiGraph()
        eng = NetworkXEngine(g)
        assert eng.node_count() == 0
        assert eng.average_edge_probability() == 0.0
        assert eng.find_cliques() == []

    def test_single_node(self):
        g = nx.DiGraph()
        g.add_node(1)
        eng = NetworkXEngine(g)
        assert eng.node_count() == 1
        # single node gets eigenvector=1.0 (trivial normalization)
        assert isinstance(eng.eigenvector_centrality(1), float)
        assert isinstance(eng.pagerank(1), float)
