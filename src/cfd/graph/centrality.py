"""Extended centrality indicators via GraphEngine."""

from __future__ import annotations

from typing import Any

from cfd.graph.engine import GraphEngine
from cfd.graph.metrics import IndicatorResult


def compute_eigenvector_centrality(engine: GraphEngine, node_id: Any) -> IndicatorResult:
    """Eigenvector centrality for a node."""
    value = engine.eigenvector_centrality(node_id)
    return IndicatorResult(
        "EIGEN",
        value,
        {"node_id": node_id, "metric": "eigenvector_centrality"},
    )


def compute_betweenness_centrality(engine: GraphEngine, node_id: Any) -> IndicatorResult:
    """Betweenness centrality for a node."""
    value = engine.betweenness_centrality(node_id)
    return IndicatorResult(
        "BETWEENNESS",
        value,
        {"node_id": node_id, "metric": "betweenness_centrality"},
    )


def compute_pagerank(engine: GraphEngine, node_id: Any) -> IndicatorResult:
    """PageRank score for a node."""
    value = engine.pagerank(node_id)
    return IndicatorResult(
        "PAGERANK",
        value,
        {"node_id": node_id, "metric": "pagerank"},
    )
