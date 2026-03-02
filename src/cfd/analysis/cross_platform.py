"""Cross-Platform Consistency Check (CPC) indicator."""

from __future__ import annotations

import logging

from cfd.data.models import AuthorData, AuthorProfile, Publication
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_cpc(
    author_data: AuthorData,
    secondary_strategy=None,
    divergence_threshold: float = 0.20,
) -> IndicatorResult:
    """Cross-Platform Consistency: compare metrics between OpenAlex and Scopus.

    Compare publication_count, citation_count, h_index.
    >20% divergence on any metric = warning signal.
    Fuzzy publication matching by DOI, title.

    Returns IndicatorResult("CPC", value, details).
    """
    if not secondary_strategy:
        return IndicatorResult(
            indicator_type="CPC",
            value=0.0,
            details={"status": "single_source"},
        )

    # Fetch secondary profile
    secondary_profile = _fetch_secondary_profile(author_data, secondary_strategy)
    if not secondary_profile:
        return IndicatorResult(
            indicator_type="CPC",
            value=0.0,
            details={"status": "secondary_api_failed"},
        )

    primary = author_data.profile

    # Compute metric divergences
    divergences = _compute_metric_divergences(primary, secondary_profile)

    # Count divergent metrics
    divergent_count = sum(
        1 for d in divergences.values()
        if d["divergence"] is not None and d["divergence"] > divergence_threshold
    )
    total_metrics = sum(1 for d in divergences.values() if d["divergence"] is not None)

    value = (divergent_count / total_metrics) if total_metrics > 0 else 0.0
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        indicator_type="CPC",
        value=value,
        details={
            "divergences": divergences,
            "divergent_count": divergent_count,
            "total_metrics": total_metrics,
            "divergence_threshold": divergence_threshold,
            "primary_source": primary.source_api,
            "secondary_source": secondary_profile.source_api,
        },
    )


def _fetch_secondary_profile(
    author_data: AuthorData,
    secondary_strategy,
) -> AuthorProfile | None:
    """Fetch author profile from secondary API."""
    try:
        return secondary_strategy.fetch_author(
            author_data.profile.surname,
            scopus_id=author_data.profile.scopus_id,
            orcid=author_data.profile.orcid,
        )
    except Exception:
        logger.warning("Failed to fetch secondary profile", exc_info=True)
        return None


def _compute_metric_divergences(
    primary: AuthorProfile,
    secondary: AuthorProfile,
) -> dict[str, dict]:
    """Compute relative divergence for each metric."""
    metrics = {
        "publication_count": (primary.publication_count, secondary.publication_count),
        "citation_count": (primary.citation_count, secondary.citation_count),
        "h_index": (primary.h_index, secondary.h_index),
    }

    divergences = {}
    for name, (p_val, s_val) in metrics.items():
        if p_val is not None and s_val is not None:
            denominator = max(p_val, s_val, 1)
            div = abs(p_val - s_val) / denominator
            divergences[name] = {
                "primary": p_val,
                "secondary": s_val,
                "divergence": round(div, 4),
            }
        else:
            divergences[name] = {
                "primary": p_val,
                "secondary": s_val,
                "divergence": None,
            }

    return divergences


def fuzzy_publication_match(
    primary_pubs: list[Publication],
    secondary_pubs: list[Publication],
) -> dict:
    """Match publications across platforms using DOI and title similarity."""
    matched_by_doi = 0
    matched_by_title = 0
    unmatched = 0

    secondary_dois = {p.doi.lower() for p in secondary_pubs if p.doi}
    secondary_titles = {p.title.lower().strip() for p in secondary_pubs if p.title}

    for pub in primary_pubs:
        if pub.doi and pub.doi.lower() in secondary_dois:
            matched_by_doi += 1
        elif pub.title and _best_title_match(pub.title, secondary_titles) >= 0.8:
            matched_by_title += 1
        else:
            unmatched += 1

    total = len(primary_pubs)
    overlap = (matched_by_doi + matched_by_title) / total if total > 0 else 0.0

    return {
        "matched_by_doi": matched_by_doi,
        "matched_by_title": matched_by_title,
        "unmatched": unmatched,
        "total_primary": total,
        "total_secondary": len(secondary_pubs),
        "overlap_ratio": round(overlap, 4),
    }


def _best_title_match(title: str, title_set: set[str]) -> float:
    """Find best Jaccard similarity of title against a set of titles."""
    words_a = set(title.lower().split())
    best = 0.0
    for other in title_set:
        words_b = set(other.split())
        if not words_a or not words_b:
            continue
        jaccard = len(words_a & words_b) / len(words_a | words_b)
        if jaccard > best:
            best = jaccard
    return best
