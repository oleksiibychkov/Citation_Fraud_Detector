"""k-Clique detection and classification (Theorem 3 severity)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from cfd.graph.engine import GraphEngine
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


@dataclass
class CliqueResult:
    """A detected k-clique with metadata."""

    members: set
    size: int
    citation_density: float
    probability: float
    severity: str


def classify_clique(k: int, probability: float) -> str:
    """Classify clique severity based on size and probability.

    k <= 4 and probability > 0.01  → Low
    k <= 4 and probability <= 0.01 → Moderate
    k == 5                         → Moderate
    k == 6                         → High
    k >= 7                         → Critical
    """
    if k >= 7:
        return "Critical"
    if k == 6:
        return "High"
    if k == 5:
        return "Moderate"
    # k <= 4
    if probability <= 0.01:
        return "Moderate"
    return "Low"


def _compute_clique_probability(n: int, k: int, p: float) -> float:
    """Compute probability of a k-clique appearing by chance in log-space.

    P(clique of size k) ≈ C(n, k) * p^(k*(k-1)/2)

    Uses log-space to avoid overflow.
    """
    if p <= 0 or n < k:
        return 0.0
    if p >= 1.0:
        return 1.0

    # log C(n, k) = sum(log(n-i) - log(i+1), i=0..k-1)
    log_comb = sum(math.log(n - i) - math.log(i + 1) for i in range(k))

    # Number of edges in k-clique
    edges = k * (k - 1) / 2
    log_prob = log_comb + edges * math.log(p)

    # Clamp to avoid overflow
    if log_prob > 0:
        return min(math.exp(log_prob), 1.0)
    return math.exp(log_prob)


def detect_cliques(
    engine: GraphEngine,
    *,
    min_size: int = 3,
) -> list[CliqueResult]:
    """Detect all k-cliques (k >= min_size) and classify them."""
    raw_cliques = engine.find_cliques(min_size=min_size)
    if not raw_cliques:
        return []

    avg_p = engine.average_edge_probability()
    n = engine.node_count()

    results = []
    for members in raw_cliques:
        k = len(members)
        density = engine.subgraph_density(members)
        probability = _compute_clique_probability(n, k, avg_p)
        severity = classify_clique(k, probability)

        results.append(CliqueResult(
            members=members,
            size=k,
            citation_density=round(density, 6),
            probability=probability,
            severity=severity,
        ))

    # Sort by severity (Critical first) then by size descending
    severity_order = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    results.sort(key=lambda r: (severity_order.get(r.severity, 99), -r.size))

    return results


def clique_to_indicator(clique_results: list[CliqueResult]) -> IndicatorResult:
    """Convert clique detection results to an IndicatorResult for scoring.

    Value based on the worst severity found.
    """
    if not clique_results:
        return IndicatorResult("CLIQUE", 0.0, {"status": "no_cliques"})

    severity_scores = {"Low": 0.2, "Moderate": 0.4, "High": 0.7, "Critical": 1.0}
    worst = max(clique_results, key=lambda r: severity_scores.get(r.severity, 0))
    value = severity_scores.get(worst.severity, 0.0)

    return IndicatorResult(
        "CLIQUE",
        value,
        {
            "total_cliques": len(clique_results),
            "max_clique_size": max(r.size for r in clique_results),
            "worst_severity": worst.severity,
            "severities": {s: sum(1 for r in clique_results if r.severity == s) for s in severity_scores},
        },
    )
