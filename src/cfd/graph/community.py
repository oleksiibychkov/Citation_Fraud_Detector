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

    Improved non-binary scoring based on:
    1. Proportion of suspicious communities among eligible ones.
    2. Weighted severity from density ratios (higher ratio = more suspicious).
    3. Isolation penalty for communities with zero external density.

    Final score = 0.5 * proportion + 0.3 * severity + 0.2 * isolation_factor
    """
    suspicious = result.suspicious_communities

    # Count only communities large enough to be evaluated
    eligible = sum(1 for m in result.communities.values() if len(m) >= min_community_size)

    if eligible == 0:
        return IndicatorResult("COMMUNITY", 0.0, {"status": "no_eligible_communities"})

    # Component 1: proportion of suspicious communities
    proportion = len(suspicious) / eligible

    # Component 2: severity from density ratios (capped at 10x threshold)
    max_ratio = 0.0
    avg_ratio = 0.0
    isolated_count = 0
    if suspicious:
        ratios = []
        for s in suspicious:
            r = s.get("density_ratio", 0.0)
            if r == float("inf") or s.get("isolated"):
                isolated_count += 1
                ratios.append(10.0)  # cap isolated to max
            else:
                ratios.append(min(r, 10.0))
        max_ratio = max(ratios)
        avg_ratio = sum(ratios) / len(ratios)
    severity = min(avg_ratio / 10.0, 1.0)  # normalize to [0, 1]

    # Component 3: isolation factor — communities with zero external links
    isolation_factor = isolated_count / eligible if eligible > 0 else 0.0

    value = 0.5 * proportion + 0.3 * severity + 0.2 * isolation_factor
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        "COMMUNITY",
        round(value, 6),
        {
            "eligible_communities": eligible,
            "suspicious_count": len(suspicious),
            "isolated_count": isolated_count,
            "max_density_ratio": round(max_ratio, 4),
            "avg_density_ratio": round(avg_ratio, 4),
            "modularity": round(result.modularity, 4),
        },
    )
