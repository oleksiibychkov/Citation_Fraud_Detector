"""Community detection via Louvain algorithm."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cfd.graph.engine import GraphEngine
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


@dataclass
class CommunityResult:
    """Result of community detection."""

    partition: dict[Any, int] = field(default_factory=dict)
    modularity: float = 0.0
    communities: dict[int, set] = field(default_factory=dict)
    suspicious_communities: list[dict] = field(default_factory=list)


def detect_communities(
    engine: GraphEngine,
    *,
    density_ratio_threshold: float = 2.0,
    min_community_size: int = 3,
) -> CommunityResult:
    """Run Louvain community detection and identify suspicious communities.

    A community is suspicious if:
    - internal_density / external_density > density_ratio_threshold
    - community size >= min_community_size
    """
    partition = engine.louvain_communities()
    if not partition:
        return CommunityResult()

    mod = engine.modularity(partition)

    # Group nodes by community
    communities: dict[int, set] = {}
    for node, cid in partition.items():
        communities.setdefault(cid, set()).add(node)

    suspicious = []
    for cid, members in communities.items():
        if len(members) < min_community_size:
            continue

        internal_d, external_d = engine.community_densities(members)
        ratio = internal_d / external_d if external_d > 0 else float("inf")

        if ratio > density_ratio_threshold:
            suspicious.append({
                "community_id": cid,
                "member_count": len(members),
                "member_ids": sorted(members),
                "internal_density": round(internal_d, 6),
                "external_density": round(external_d, 6),
                "density_ratio": round(ratio, 4),
            })

    return CommunityResult(
        partition=partition,
        modularity=mod,
        communities=communities,
        suspicious_communities=suspicious,
    )


def community_to_indicator(result: CommunityResult) -> IndicatorResult:
    """Convert community detection result to an IndicatorResult for scoring.

    Value is based on the proportion of suspicious communities.
    """
    total = len(result.communities)
    suspicious_count = len(result.suspicious_communities)

    if total == 0:
        return IndicatorResult("COMMUNITY", 0.0, {"status": "no_communities"})

    value = suspicious_count / total
    return IndicatorResult(
        "COMMUNITY",
        round(min(value, 1.0), 6),
        {
            "total_communities": total,
            "suspicious_count": suspicious_count,
            "modularity": round(result.modularity, 4),
        },
    )
