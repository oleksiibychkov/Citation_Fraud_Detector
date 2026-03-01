"""Tests for extended centrality indicators."""

import networkx as nx

from cfd.graph.centrality import (
    compute_betweenness_centrality,
    compute_eigenvector_centrality,
    compute_pagerank,
)
from cfd.graph.engine import NetworkXEngine


def _make_engine():
    g = nx.DiGraph()
    g.add_weighted_edges_from([
        (1, 2, 1.0), (2, 1, 1.0),
        (2, 3, 1.0), (3, 2, 1.0),
        (3, 1, 1.0), (1, 3, 1.0),
        (4, 1, 1.0), (4, 2, 1.0),
    ])
    return NetworkXEngine(g)


class TestComputeEigenvectorCentrality:
    def test_returns_indicator_result(self):
        engine = _make_engine()
        result = compute_eigenvector_centrality(engine, 1)
        assert result.indicator_type == "EIGEN"
        assert isinstance(result.value, float)
        assert 0.0 <= result.value <= 1.0

    def test_missing_node_returns_zero(self):
        engine = _make_engine()
        result = compute_eigenvector_centrality(engine, 999)
        assert result.value == 0.0

    def test_details_contain_node_id(self):
        engine = _make_engine()
        result = compute_eigenvector_centrality(engine, 1)
        assert result.details["node_id"] == 1
        assert result.details["metric"] == "eigenvector_centrality"


class TestComputeBetweennessCentrality:
    def test_returns_indicator_result(self):
        engine = _make_engine()
        result = compute_betweenness_centrality(engine, 1)
        assert result.indicator_type == "BETWEENNESS"
        assert isinstance(result.value, float)

    def test_missing_node_returns_zero(self):
        engine = _make_engine()
        result = compute_betweenness_centrality(engine, 999)
        assert result.value == 0.0


class TestComputePagerank:
    def test_returns_indicator_result(self):
        engine = _make_engine()
        result = compute_pagerank(engine, 1)
        assert result.indicator_type == "PAGERANK"
        assert isinstance(result.value, float)
        assert result.value > 0.0

    def test_missing_node_returns_zero(self):
        engine = _make_engine()
        result = compute_pagerank(engine, 999)
        assert result.value == 0.0

    def test_details_contain_metric(self):
        engine = _make_engine()
        result = compute_pagerank(engine, 1)
        assert result.details["metric"] == "pagerank"
