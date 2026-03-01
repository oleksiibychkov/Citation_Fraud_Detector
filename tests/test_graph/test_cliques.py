"""Tests for clique detection and classification."""

import networkx as nx

from cfd.graph.cliques import (
    CliqueResult,
    _compute_clique_probability,
    classify_clique,
    clique_to_indicator,
    detect_cliques,
)
from cfd.graph.engine import NetworkXEngine


class TestClassifyClique:
    def test_k3_high_prob(self):
        assert classify_clique(3, 0.5) == "Low"

    def test_k4_low_prob(self):
        assert classify_clique(4, 0.001) == "Moderate"

    def test_k5(self):
        assert classify_clique(5, 0.1) == "Moderate"

    def test_k6(self):
        assert classify_clique(6, 0.001) == "High"

    def test_k7(self):
        assert classify_clique(7, 0.001) == "Critical"

    def test_k10(self):
        assert classify_clique(10, 0.0) == "Critical"


class TestComputeCliqueProbability:
    def test_zero_probability_edge(self):
        assert _compute_clique_probability(100, 3, 0.0) == 0.0

    def test_full_graph(self):
        result = _compute_clique_probability(10, 3, 1.0)
        assert result == 1.0

    def test_returns_small_for_large_clique(self):
        result = _compute_clique_probability(100, 7, 0.01)
        assert result < 0.01

    def test_n_less_than_k(self):
        assert _compute_clique_probability(2, 5, 0.5) == 0.0


class TestDetectCliques:
    def test_triangle_detected(self):
        g = nx.Graph()
        g.add_weighted_edges_from([(1, 2, 1.0), (2, 3, 1.0), (1, 3, 1.0)])
        engine = NetworkXEngine(g)
        results = detect_cliques(engine, min_size=3)
        assert len(results) >= 1
        assert results[0].size == 3

    def test_no_cliques(self):
        g = nx.Graph()
        g.add_edge(1, 2, weight=1.0)
        engine = NetworkXEngine(g)
        results = detect_cliques(engine, min_size=3)
        assert results == []

    def test_larger_clique(self):
        # K4 graph
        g = nx.complete_graph(4)
        for u, v in g.edges():
            g[u][v]["weight"] = 1.0
        engine = NetworkXEngine(g)
        results = detect_cliques(engine, min_size=3)
        # Should find at least one clique of size 4
        sizes = [r.size for r in results]
        assert 4 in sizes

    def test_sorted_by_severity(self):
        # K5 graph → cliques of various sizes
        g = nx.complete_graph(6)
        for u, v in g.edges():
            g[u][v]["weight"] = 1.0
        engine = NetworkXEngine(g)
        results = detect_cliques(engine, min_size=3)
        if len(results) > 1:
            severity_order = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
            for i in range(len(results) - 1):
                s1 = severity_order.get(results[i].severity, 99)
                s2 = severity_order.get(results[i + 1].severity, 99)
                assert s1 <= s2


class TestCliqueToIndicator:
    def test_no_cliques(self):
        ind = clique_to_indicator([])
        assert ind.indicator_type == "CLIQUE"
        assert ind.value == 0.0

    def test_low_severity(self):
        cliques = [CliqueResult(members={1, 2, 3}, size=3, citation_density=1.0, probability=0.5, severity="Low")]
        ind = clique_to_indicator(cliques)
        assert ind.value == 0.2

    def test_critical_severity(self):
        cliques = [
            CliqueResult(members=set(range(7)), size=7, citation_density=1.0, probability=0.0001, severity="Critical"),
        ]
        ind = clique_to_indicator(cliques)
        assert ind.value == 1.0

    def test_details(self):
        cliques = [
            CliqueResult(members={1, 2, 3}, size=3, citation_density=1.0, probability=0.5, severity="Low"),
            CliqueResult(members={4, 5, 6, 7}, size=4, citation_density=0.8, probability=0.01, severity="Moderate"),
        ]
        ind = clique_to_indicator(cliques)
        assert ind.details["total_cliques"] == 2
        assert ind.details["max_clique_size"] == 4
        assert ind.details["worst_severity"] == "Moderate"
