"""Tests for IGraphEngine."""

from __future__ import annotations

import pytest

ig = pytest.importorskip("igraph")

import networkx as nx  # noqa: E402

from cfd.graph.igraph_engine import IGraphEngine  # noqa: E402


@pytest.fixture
def simple_graph():
    """Create a simple directed graph for testing."""
    g = nx.DiGraph()
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("B", "C", weight=1.0)
    g.add_edge("C", "A", weight=1.0)
    g.add_edge("A", "D", weight=1.0)
    g.add_edge("D", "B", weight=1.0)
    return g


@pytest.fixture
def engine(simple_graph):
    return IGraphEngine(simple_graph)


class TestConstruction:
    def test_node_count(self, engine):
        assert engine.node_count() == 4

    def test_from_undirected(self):
        g = nx.Graph()
        g.add_edge("X", "Y", weight=2.0)
        g.add_edge("Y", "Z", weight=1.0)
        e = IGraphEngine(g)
        assert e.node_count() == 3


class TestCentrality:
    def test_eigenvector(self, engine):
        score = engine.eigenvector_centrality("A")
        assert isinstance(score, float)
        assert score >= 0.0

    def test_eigenvector_missing_node(self, engine):
        assert engine.eigenvector_centrality("MISSING") == 0.0

    def test_betweenness(self, engine):
        score = engine.betweenness_centrality("B")
        assert isinstance(score, float)
        assert score >= 0.0

    def test_pagerank(self, engine):
        score = engine.pagerank("A")
        assert isinstance(score, float)
        assert score > 0.0

    def test_pagerank_sums_to_one(self, engine):
        total = sum(engine.pagerank(n) for n in ["A", "B", "C", "D"])
        assert abs(total - 1.0) < 0.01


class TestCommunities:
    def test_louvain(self, engine):
        partition = engine.louvain_communities()
        assert set(partition.keys()) == {"A", "B", "C", "D"}
        assert all(isinstance(v, int) for v in partition.values())

    def test_modularity(self, engine):
        partition = engine.louvain_communities()
        mod = engine.modularity(partition)
        assert isinstance(mod, float)


class TestCliques:
    def test_find_cliques(self):
        g = nx.Graph()
        g.add_edges_from([("A", "B"), ("B", "C"), ("A", "C"), ("C", "D")])
        e = IGraphEngine(g)
        cliques = e.find_cliques(min_size=3)
        assert len(cliques) >= 1
        assert {"A", "B", "C"} in cliques

    def test_no_cliques(self):
        g = nx.Graph()
        g.add_edge("A", "B")
        e = IGraphEngine(g)
        assert e.find_cliques(min_size=3) == []


class TestCycleDetection:
    def test_has_cycle(self, engine):
        assert engine.has_cycle_in_subgraph({"A", "B", "C"}) is True

    def test_no_cycle(self):
        g = nx.DiGraph()
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        e = IGraphEngine(g)
        assert e.has_cycle_in_subgraph({"A", "B", "C"}) is False


class TestDensity:
    def test_subgraph_density(self, engine):
        d = engine.subgraph_density({"A", "B", "C"})
        assert isinstance(d, float)
        assert 0.0 <= d <= 1.0

    def test_average_edge_probability(self, engine):
        p = engine.average_edge_probability()
        assert isinstance(p, float)
        assert 0.0 < p <= 1.0

    def test_single_node(self):
        g = nx.DiGraph()
        g.add_node("X")
        e = IGraphEngine(g)
        assert e.average_edge_probability() == 0.0
