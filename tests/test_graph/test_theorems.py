"""Tests for Theorems 1-3 mathematical hierarchy."""

import networkx as nx

from cfd.graph.cliques import CliqueResult
from cfd.graph.engine import NetworkXEngine
from cfd.graph.theorems import (
    run_hierarchy,
    theorem1_acyclicity_filter,
    theorem2_statistical_test,
    theorem3_structural_test,
)


class TestTheorem1:
    def test_cyclic_graph_passes(self):
        """Directed cycle → passed=True (suspicious)."""
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        engine = NetworkXEngine(g)
        result = theorem1_acyclicity_filter(engine, {1, 2, 3})
        assert result.theorem_number == 1
        assert result.passed is True
        assert result.details["has_cycle"] is True

    def test_acyclic_graph_fails(self):
        """DAG → passed=False (no cycle evidence)."""
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        engine = NetworkXEngine(g)
        result = theorem1_acyclicity_filter(engine, {1, 2, 3})
        assert result.passed is False
        assert result.details["has_cycle"] is False

    def test_small_subset(self):
        """Subset with < 2 nodes → passed=False."""
        g = nx.DiGraph()
        g.add_node(1)
        engine = NetworkXEngine(g)
        result = theorem1_acyclicity_filter(engine, {1})
        assert result.passed is False
        assert result.details["status"] == "subset_too_small"


class TestTheorem2:
    def test_significant_deviation(self):
        """Large z-score → passed=True."""
        result = theorem2_statistical_test(mu_s=0.6, mu_d=0.15, sigma_d=0.1, z_threshold=3.0)
        assert result.theorem_number == 2
        assert result.passed is True
        assert result.details["z_score"] == 4.5

    def test_not_significant(self):
        """Small z-score → passed=False."""
        result = theorem2_statistical_test(mu_s=0.2, mu_d=0.15, sigma_d=0.1, z_threshold=3.0)
        assert result.passed is False
        assert result.details["z_score"] == 0.5

    def test_zero_std(self):
        """Zero std → passed=False (cannot compute)."""
        result = theorem2_statistical_test(mu_s=0.5, mu_d=0.15, sigma_d=0.0)
        assert result.passed is False
        assert result.details["status"] == "zero_std"

    def test_cantelli_probability(self):
        """Verify Cantelli probability P ≤ 1/(1+z²)."""
        result = theorem2_statistical_test(mu_s=0.45, mu_d=0.15, sigma_d=0.1)
        z = result.details["z_score"]
        expected_prob = 1.0 / (1.0 + z * z)
        assert abs(result.details["cantelli_probability"] - expected_prob) < 0.001


class TestTheorem3:
    def test_no_cliques(self):
        result = theorem3_structural_test([])
        assert result.theorem_number == 3
        assert result.passed is False

    def test_small_cliques_only(self):
        """Only cliques of size 3-4 → passed=False."""
        cliques = [
            CliqueResult(members={1, 2, 3}, size=3, citation_density=1.0, probability=0.5, severity="Low"),
            CliqueResult(members={4, 5, 6, 7}, size=4, citation_density=0.8, probability=0.1, severity="Moderate"),
        ]
        result = theorem3_structural_test(cliques)
        assert result.passed is False

    def test_significant_clique(self):
        """Clique of size ≥ 5 → passed=True."""
        cliques = [
            CliqueResult(members={1, 2, 3, 4, 5}, size=5, citation_density=1.0, probability=0.001, severity="Moderate"),
        ]
        result = theorem3_structural_test(cliques)
        assert result.passed is True
        assert result.details["significant_cliques"] == 1

    def test_large_clique(self):
        """k=7 → Critical + passed=True."""
        cliques = [
            CliqueResult(
                members=set(range(7)), size=7,
                citation_density=1.0, probability=0.00001, severity="Critical",
            ),
        ]
        result = theorem3_structural_test(cliques)
        assert result.passed is True
        assert result.details["max_clique_size"] == 7


class TestRunHierarchy:
    def _make_cyclic_engine(self):
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3), (3, 1)])
        return NetworkXEngine(g)

    def _make_acyclic_engine(self):
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3)])
        return NetworkXEngine(g)

    def test_early_exit_at_t1(self):
        """Acyclic graph → only T1 result returned."""
        engine = self._make_acyclic_engine()
        results = run_hierarchy(engine, {1, 2, 3}, mu_s=0.5, mu_d=0.15, sigma_d=0.1, clique_results=[])
        assert len(results) == 1
        assert results[0].theorem_number == 1
        assert results[0].passed is False

    def test_early_exit_at_t2(self):
        """Cyclic but not significant → T1 + T2."""
        engine = self._make_cyclic_engine()
        results = run_hierarchy(
            engine, {1, 2, 3},
            mu_s=0.2, mu_d=0.15, sigma_d=0.1,  # z=0.5 < 3.0
            clique_results=[],
        )
        assert len(results) == 2
        assert results[0].passed is True   # T1: cycles found
        assert results[1].passed is False  # T2: not significant

    def test_full_hierarchy(self):
        """All three theorems pass."""
        engine = self._make_cyclic_engine()
        cliques = [
            CliqueResult(members={1, 2, 3, 4, 5}, size=5, citation_density=1.0, probability=0.001, severity="Moderate"),
        ]
        results = run_hierarchy(
            engine, {1, 2, 3},
            mu_s=0.6, mu_d=0.15, sigma_d=0.1,  # z=4.5 > 3.0
            clique_results=cliques,
        )
        assert len(results) == 3
        assert all(r.passed for r in results)
