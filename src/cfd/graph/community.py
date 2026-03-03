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
        if external_d == 0.0:
            # Isolated community with internal edges is highly suspicious
            if internal_d > 0:
                suspicious.append({
                    "community_id": cid,
                    "member_count": len(members),
                    "member_ids": sorted(members),
                    "internal_density": round(internal_d, 6),
                    "external_density": 0.0,
                    "density_ratio": float("inf"),
                    "isolated": True,
                })
            continue
        ratio = internal_d / external_d

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


def community_to_indicator(result: CommunityResult, min_community_size: int = 3) -> IndicatorResult:
    """Convert community detection result to an IndicatorResult for scoring.

    Value is based on the proportion of suspicious communities among eligible ones.
    """
    suspicious_count = len(result.suspicious_communities)

    # Count only communities large enough to be evaluated
    eligible = sum(1 for m in result.communities.values() if len(m) >= min_community_size)

    if eligible == 0:
        return IndicatorResult("COMMUNITY", 0.0, {"status": "no_eligible_communities"})

    value = suspicious_count / eligible
    return IndicatorResult(
        "COMMUNITY",
        round(min(value, 1.0), 6),
        {
            "eligible_communities": eligible,
            "suspicious_count": suspicious_count,
            "modularity": round(result.modularity, 4),
        },
    )
