"""Peer Benchmark (PB) indicator."""

from __future__ import annotations

import logging
import math

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_pb(
    author_data: AuthorData,
    peer_repo=None,
    author_repo=None,
    k: int = 10,
    min_peers: int = 3,
    author_id: int | None = None,
) -> IndicatorResult:
    """Peer Benchmark: compare author metrics with k-NN matched peers.

    Matching: discipline + publication_count ±50% + career_start_year ±3.
    Compare: h_index, citation_count, publication_count.
    Z-score deviation from peer median.

    Returns IndicatorResult("PB", value, details).
    """
    if not peer_repo or not author_repo:
        return IndicatorResult(
            indicator_type="PB",
            value=0.0,
            details={"status": "no_db_connection"},
        )

    # Find peers
    peers = _find_peers(author_data, author_repo, peer_repo, k)

    if len(peers) < min_peers:
        return IndicatorResult(
            indicator_type="PB",
            value=0.0,
            details={"status": "insufficient_peers", "peer_count": len(peers), "min_required": min_peers},
        )

    # Compute deviations
    author_metrics = {
        "h_index": author_data.profile.h_index or 0,
        "citation_count": author_data.profile.citation_count or 0,
        "publication_count": author_data.profile.publication_count or 0,
    }

    deviations = _compute_peer_deviation(author_metrics, peers)

    # PB = mean(|z_i|) / 3, capped [0, 1]
    z_values = [abs(d["z_score"]) for d in deviations.values() if d["z_score"] is not None]
    value = (sum(z_values) / len(z_values) / 3.0) if z_values else 0.0
    value = min(max(value, 0.0), 1.0)

    # Save peer group if repo available
    try:
        if peer_repo and hasattr(peer_repo, "save") and author_id is not None:
            peer_ids = [p.get("id") for p in peers if p.get("id")]
            peer_repo.save(
                author_id=author_id,
                peer_author_ids=peer_ids,
                discipline=author_data.profile.discipline or "unknown",
                matching_criteria={"k": k, "min_peers": min_peers},
            )
    except Exception:
        logger.warning("Failed to save peer group", exc_info=True)

    return IndicatorResult(
        indicator_type="PB",
        value=value,
        details={
            "peer_count": len(peers),
            "deviations": {
                dk: {"z_score": round(dv["z_score"], 4) if dv["z_score"] is not None else None, **dv}
                for dk, dv in deviations.items()
            },
            "author_metrics": author_metrics,
        },
    )


def _find_peers(
    author_data: AuthorData,
    author_repo,
    peer_repo,
    k: int = 10,
) -> list[dict]:
    """Find k nearest peers from already-analyzed authors in DB."""
    discipline = author_data.profile.discipline
    pub_count = author_data.profile.publication_count or 0

    if not discipline:
        return []

    min_pubs = max(1, int(pub_count * 0.5))
    max_pubs = int(pub_count * 1.5) + 1

    try:
        if hasattr(peer_repo, "find_peers"):
            return peer_repo.find_peers(
                discipline=discipline,
                min_pubs=min_pubs,
                max_pubs=max_pubs,
                limit=k,
            )
    except Exception:
        logger.warning("Peer search failed", exc_info=True)

    return []


def _compute_peer_deviation(
    author_metrics: dict,
    peers: list[dict],
) -> dict:
    """Compute Z-score deviation of author from peer median for each metric."""
    deviations = {}

    for metric in ("h_index", "citation_count", "publication_count"):
        peer_values = [p.get(metric, 0) or 0 for p in peers]
        if not peer_values:
            deviations[metric] = {"z_score": None, "peer_median": None, "peer_std": None}
            continue

        peer_values_sorted = sorted(peer_values)
        n = len(peer_values_sorted)
        mid = n // 2
        median = peer_values_sorted[mid] if n % 2 == 1 else (peer_values_sorted[mid - 1] + peer_values_sorted[mid]) / 2

        mean = sum(peer_values) / n
        variance = sum((v - mean) ** 2 for v in peer_values) / (n - 1) if n > 1 else 0.0
        std = math.sqrt(variance) if variance > 0 else 0.0

        author_val = author_metrics.get(metric, 0)
        z_score = (author_val - median) / std if std > 0 else 0.0

        deviations[metric] = {
            "z_score": z_score,
            "peer_median": median,
            "peer_std": round(std, 4),
            "author_value": author_val,
        }

    return deviations
