"""Citation Ring (directed cycle) detection indicator."""

from __future__ import annotations

import logging
import math

from cfd.graph.engine import GraphEngine
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def _compute_cycle_probability(n: int, k: int, p: float) -> float:
    """Probability of a directed cycle of length k in a random graph.

    P(cycle of length k) ≈ (n choose k) * k! / (2k) * p^k

    For a directed graph with n nodes and edge probability p,
    the expected number of directed cycles of length k is:
    E[cycles] = (n choose k) * (k-1)! / 2 * p^k

    Uses log-space to avoid overflow.
    """
    if p <= 0 or n < k or k < 2:
        return 0.0
    if p >= 1.0:
        return 1.0

    # log C(n,k) = sum(log(n-i) - log(i+1))
    log_comb = sum(math.log(n - i) - math.log(i + 1) for i in range(k))

    # log((k-1)!/2)
    log_factorial = sum(math.log(i) for i in range(1, k))  # (k-1)!
    log_factorial -= math.log(2)

    log_prob = log_comb + log_factorial + k * math.log(p)

    if log_prob > 0:
        return min(math.exp(log_prob), 1.0)
    return math.exp(log_prob)


def detect_rings(
    engine: GraphEngine,
    author_work_ids: set[str],
    *,
    min_length: int = 3,
    max_length: int = 8,
    max_rings: int = 50,
) -> list[dict]:
    """Detect directed citation rings (cycles) involving the author's works.

    A citation ring is a directed cycle: A cites B, B cites C, C cites A.
    Unlike cliques (mutual citation), rings are one-directional and harder to detect.

    Returns list of ring dicts with members, length, probability, severity.
    """
    import networkx as nx

    # Need access to the underlying NetworkX graph
    if not hasattr(engine, "_g"):
        return []

    graph = engine._g
    if not isinstance(graph, (nx.DiGraph,)):
        return []

    if len(graph.nodes) < min_length:
        return []

    avg_p = engine.average_edge_probability()
    n = engine.node_count()

    rings = []
    seen_sets = set()

    try:
        # Find simple cycles in the directed graph
        cycle_iter = nx.simple_cycles(graph)
        count = 0
        for cycle in cycle_iter:
            if count >= max_rings * 10:  # limit search
                break
            count += 1

            k = len(cycle)
            if k < min_length or k > max_length:
                continue

            # Only include rings that involve the author's works
            cycle_set = frozenset(cycle)
            if not (cycle_set & author_work_ids):
                continue

            if cycle_set in seen_sets:
                continue
            seen_sets.add(cycle_set)

            probability = _compute_cycle_probability(n, k, avg_p)
            severity = _classify_ring(k, probability)

            rings.append({
                "members": list(cycle),
                "length": k,
                "probability": probability,
                "severity": severity,
            })

            if len(rings) >= max_rings:
                break

    except Exception:
        logger.warning("Cycle detection failed", exc_info=True)

    # Sort: most severe first, then longest
    severity_order = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    rings.sort(key=lambda r: (severity_order.get(r["severity"], 99), -r["length"]))

    return rings


def _classify_ring(k: int, probability: float) -> str:
    """Classify ring severity based on length and random probability."""
    if k >= 6:
        return "Critical"
    if k == 5:
        return "High"
    if k == 4:
        return "Moderate" if probability < 0.01 else "Low"
    # k == 3
    if probability < 0.001:
        return "Moderate"
    return "Low"


def rings_to_indicator(rings: list[dict], total_works: int) -> IndicatorResult:
    """Convert ring detection results to an IndicatorResult.

    Score based on:
    - Number of rings found
    - Worst severity
    - Fraction of author's works involved in rings
    """
    if not rings:
        return IndicatorResult("RING", 0.0, {"status": "no_rings"})

    severity_scores = {"Low": 0.2, "Moderate": 0.4, "High": 0.7, "Critical": 1.0}
    worst = max(rings, key=lambda r: severity_scores.get(r["severity"], 0))
    worst_score = severity_scores.get(worst["severity"], 0.0)

    # Count unique author works involved in any ring
    involved_works: set = set()
    for ring in rings:
        involved_works.update(ring["members"])

    involvement_ratio = len(involved_works) / max(total_works, 1)

    # Score: combine worst severity with involvement ratio
    value = 0.6 * worst_score + 0.4 * min(involvement_ratio, 1.0)
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        "RING",
        round(value, 4),
        {
            "total_rings": len(rings),
            "max_ring_length": max(r["length"] for r in rings),
            "worst_severity": worst["severity"],
            "involved_works": len(involved_works),
            "total_works": total_works,
            "involvement_ratio": round(involvement_ratio, 4),
            "rings": rings[:10],  # top 10 for details
        },
    )
