"""Mathematical hierarchy: Theorems 1-3 for citation fraud detection.

Theorem 1 (Acyclicity Filter): If a citation subgraph is acyclic, it cannot
    contain citation rings → stop (no fraud evidence from structure).

Theorem 2 (Statistical Test - Cantelli Inequality): If mean self-citation rate μ_s
    deviates from the discipline mean μ_d by more than z standard deviations,
    then P(deviation by chance) ≤ 1/(1 + z²).

Theorem 3 (Structural Test): If significant k-cliques (k ≥ 5) are found in the
    mutual citation graph, structural fraud evidence exists.

Hierarchy: T1 (acyclic → stop) → T2 (not significant → stop) → T3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cfd.graph.cliques import CliqueResult
from cfd.graph.engine import GraphEngine

logger = logging.getLogger(__name__)


@dataclass
class TheoremResult:
    """Result of a theorem evaluation."""

    theorem_number: int
    passed: bool  # True = evidence of fraud found at this level
    details: dict


def theorem1_acyclicity_filter(engine: GraphEngine, subset: set[Any]) -> TheoremResult:
    """Theorem 1: Check for cycles in the citation subgraph.

    If cycles are found → passed=True (suspicious, proceed to T2).
    If no cycles → passed=False (no structural fraud evidence, stop).
    """
    if len(subset) < 2:
        return TheoremResult(
            theorem_number=1,
            passed=False,
            details={"status": "subset_too_small", "subset_size": len(subset)},
        )

    has_cycle = engine.has_cycle_in_subgraph(subset)
    return TheoremResult(
        theorem_number=1,
        passed=has_cycle,
        details={
            "has_cycle": has_cycle,
            "subset_size": len(subset),
        },
    )


def theorem2_statistical_test(
    mu_s: float,
    mu_d: float,
    sigma_d: float,
    z_threshold: float = 3.0,
) -> TheoremResult:
    """Theorem 2: Cantelli inequality-based statistical test.

    Tests if the author's self-citation rate μ_s significantly deviates
    from the discipline mean μ_d.

    z = |μ_s - μ_d| / σ_d
    P(deviation ≥ z·σ) ≤ 1 / (1 + z²)  (Cantelli / one-sided Chebyshev)

    passed=True if z > z_threshold (statistically significant).
    """
    if sigma_d <= 0:
        return TheoremResult(
            theorem_number=2,
            passed=False,
            details={"status": "zero_std", "mu_s": mu_s, "mu_d": mu_d},
        )

    z = abs(mu_s - mu_d) / sigma_d
    cantelli_prob = 1.0 / (1.0 + z * z)
    passed = z > z_threshold

    return TheoremResult(
        theorem_number=2,
        passed=passed,
        details={
            "z_score": round(z, 4),
            "cantelli_probability": round(cantelli_prob, 6),
            "z_threshold": z_threshold,
            "mu_s": round(mu_s, 4),
            "mu_d": round(mu_d, 4),
            "sigma_d": round(sigma_d, 4),
        },
    )


def theorem3_structural_test(clique_results: list[CliqueResult]) -> TheoremResult:
    """Theorem 3: Structural test based on significant cliques.

    passed=True if any clique with size ≥ 5 is found (Moderate+ severity).
    """
    if not clique_results:
        return TheoremResult(
            theorem_number=3,
            passed=False,
            details={"status": "no_cliques"},
        )

    significant = [c for c in clique_results if c.size >= 5]
    passed = len(significant) > 0

    return TheoremResult(
        theorem_number=3,
        passed=passed,
        details={
            "total_cliques": len(clique_results),
            "significant_cliques": len(significant),
            "max_clique_size": max(c.size for c in clique_results),
            "severities": {
                s: sum(1 for c in clique_results if c.severity == s)
                for s in ("Low", "Moderate", "High", "Critical")
                if any(c.severity == s for c in clique_results)
            },
        },
    )


def run_hierarchy(
    engine: GraphEngine,
    subset: set[Any],
    mu_s: float,
    mu_d: float,
    sigma_d: float,
    clique_results: list[CliqueResult],
    z_threshold: float = 3.0,
) -> list[TheoremResult]:
    """Run the theorem hierarchy with early exit.

    T1 (acyclicity) → if acyclic, stop
    T2 (statistical) → if not significant, stop
    T3 (structural)  → final verdict
    """
    results: list[TheoremResult] = []

    # Theorem 1: Acyclicity filter
    t1 = theorem1_acyclicity_filter(engine, subset)
    results.append(t1)
    if not t1.passed:
        logger.info("Theorem 1: No cycles found → stopping hierarchy")
        return results

    # Theorem 2: Statistical test
    t2 = theorem2_statistical_test(mu_s, mu_d, sigma_d, z_threshold)
    results.append(t2)
    if not t2.passed:
        logger.info("Theorem 2: Not statistically significant → stopping hierarchy")
        return results

    # Theorem 3: Structural test
    t3 = theorem3_structural_test(clique_results)
    results.append(t3)

    return results
