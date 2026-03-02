"""Authorship Network Anomaly (ANA) indicator."""

from __future__ import annotations

import logging
from collections import Counter

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_ana(author_data: AuthorData) -> IndicatorResult:
    """Authorship Network Anomaly: detect guest/gift authorship patterns.

    Signals:
    1. Single-paper co-author ratio (one-time collaborators)
    2. Author position pattern (always middle = suspicious for prolific author)
    3. Repeat collaboration rate (low repeat = suspicious)

    Returns IndicatorResult("ANA", value, details).
    """
    stats = _extract_coauthor_stats(author_data)

    if stats["total_papers_with_coauthors"] == 0:
        return IndicatorResult(
            indicator_type="ANA",
            value=0.0,
            details={"status": "no_coauthor_data", **stats},
        )

    # Sub-signal 1: single-paper co-author ratio
    single_ratio = _single_paper_coauthor_ratio(stats)

    # Sub-signal 2: position anomaly
    position_score = _position_anomaly_score(stats, author_data)

    # Sub-signal 3: collaboration diversity (inverted repeat rate)
    diversity_score = 1.0 - stats["repeat_collaboration_rate"]

    # Weighted combination (all [0,1])
    value = 0.4 * single_ratio + 0.3 * position_score + 0.3 * diversity_score
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        indicator_type="ANA",
        value=value,
        details={
            "single_paper_coauthor_ratio": round(single_ratio, 4),
            "position_anomaly_score": round(position_score, 4),
            "collaboration_diversity_score": round(diversity_score, 4),
            **stats,
        },
    )


def _extract_coauthor_stats(author_data: AuthorData) -> dict:
    """Extract co-authorship statistics from publications."""
    coauthor_counts: Counter[str] = Counter()
    position_counts: Counter[str] = Counter()
    total_papers_with_coauthors = 0
    author_id = author_data.profile.openalex_id

    for pub in author_data.publications:
        co_authors = _get_coauthors(pub, author_id)
        if not co_authors:
            continue

        total_papers_with_coauthors += 1

        for ca in co_authors:
            ca_id = ca.get("author_id", ca.get("display_name", ""))
            if ca_id:
                coauthor_counts[ca_id] += 1

        # Track author's own position
        author_position = _find_author_position(pub, author_id)
        if author_position:
            position_counts[author_position] += 1

    unique_coauthors = len(coauthor_counts)
    single_paper_coauthors = sum(1 for count in coauthor_counts.values() if count == 1)
    repeat_coauthors = sum(1 for count in coauthor_counts.values() if count > 1)

    repeat_rate = repeat_coauthors / unique_coauthors if unique_coauthors > 0 else 0.0

    return {
        "total_papers_with_coauthors": total_papers_with_coauthors,
        "unique_coauthors": unique_coauthors,
        "single_paper_coauthors": single_paper_coauthors,
        "repeat_coauthors": repeat_coauthors,
        "repeat_collaboration_rate": round(repeat_rate, 4),
        "position_distribution": dict(position_counts),
    }


def _get_coauthors(pub, author_id: str | None) -> list[dict]:
    """Get co-authors for a publication, excluding the main author."""
    co_authors = pub.co_authors
    if not co_authors and pub.raw_data:
        # Fallback: extract from raw_data authorships
        co_authors = []
        for authorship in pub.raw_data.get("authorships", []):
            author_obj = authorship.get("author", {})
            aid = author_obj.get("id", "").replace("https://openalex.org/", "")
            co_authors.append({
                "author_id": aid,
                "display_name": author_obj.get("display_name", ""),
                "position": authorship.get("author_position", "middle"),
            })

    # Exclude the main author
    if author_id:
        co_authors = [ca for ca in co_authors if ca.get("author_id") != author_id]

    return co_authors


def _find_author_position(pub, author_id: str | None) -> str | None:
    """Find the main author's position in this publication."""
    if not author_id:
        return None

    for ca in pub.co_authors:
        if ca.get("author_id") == author_id:
            return ca.get("position")

    # Fallback: raw_data
    if pub.raw_data:
        for authorship in pub.raw_data.get("authorships", []):
            author_obj = authorship.get("author", {})
            aid = author_obj.get("id", "").replace("https://openalex.org/", "")
            if aid == author_id:
                return authorship.get("author_position")

    return None


def _single_paper_coauthor_ratio(stats: dict) -> float:
    """Fraction of co-authors who appear in only one paper."""
    if stats["unique_coauthors"] == 0:
        return 0.0
    return stats["single_paper_coauthors"] / stats["unique_coauthors"]


def _position_anomaly_score(stats: dict, author_data: AuthorData) -> float:
    """Score based on author position patterns.

    A senior author who is always in the middle position is suspicious.
    """
    positions = stats["position_distribution"]
    total = sum(positions.values())
    if total == 0:
        return 0.0

    middle_count = positions.get("middle", 0)
    middle_ratio = middle_count / total

    # Only suspicious if author has many publications (> 10)
    if (author_data.profile.publication_count or 0) < 10:
        return 0.0

    # High middle ratio for prolific author = suspicious
    return min(max(middle_ratio - 0.3, 0.0) / 0.7, 1.0)
