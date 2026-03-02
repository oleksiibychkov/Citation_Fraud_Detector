"""Salami Slicing Detector (SSD) indicator."""

from __future__ import annotations

import logging

from cfd.analysis.embeddings import EmbeddingStrategy, get_embedding_strategy
from cfd.data.models import AuthorData, Publication
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_ssd(
    author_data: AuthorData,
    embedding_strategy: EmbeddingStrategy | None = None,
    similarity_threshold: float = 0.7,
    interval_days: int = 30,
) -> IndicatorResult:
    """Salami Slicing Detector: detect paper splitting.

    1. Pairwise abstract cosine similarity → flag pairs > threshold
    2. Publication series: interval < N days + similar titles
    3. SSD = fraction of papers in suspicious pairs

    Returns IndicatorResult("SSD", value, details).
    """
    pubs = author_data.publications
    if len(pubs) < 2:
        return IndicatorResult(
            indicator_type="SSD",
            value=0.0,
            details={"status": "insufficient_publications", "total": len(pubs)},
        )

    if embedding_strategy is None:
        embedding_strategy = get_embedding_strategy()

    # Find similar pairs by abstract
    similar_pairs = _find_similar_pairs(pubs, embedding_strategy, similarity_threshold)

    # Find publication series by date + title
    series_pairs = _find_publication_series(pubs, interval_days)

    # Collect all suspicious paper IDs
    suspicious_ids: set[str] = set()
    for pair in similar_pairs:
        suspicious_ids.add(pair["work_id_a"])
        suspicious_ids.add(pair["work_id_b"])
    for pair in series_pairs:
        suspicious_ids.add(pair["work_id_a"])
        suspicious_ids.add(pair["work_id_b"])

    # Normalize
    value = min(max(len(suspicious_ids) / len(pubs), 0.0), 1.0)

    return IndicatorResult(
        indicator_type="SSD",
        value=value,
        details={
            "similar_pairs": similar_pairs[:10],
            "publication_series": series_pairs[:10],
            "suspicious_paper_count": len(suspicious_ids),
            "total_papers": len(pubs),
            "similarity_threshold": similarity_threshold,
            "interval_days": interval_days,
        },
    )


def _find_similar_pairs(
    publications: list[Publication],
    embedding_strategy: EmbeddingStrategy,
    threshold: float = 0.7,
) -> list[dict]:
    """Find pairs of papers with abstract similarity above threshold."""
    # Filter publications that have abstracts
    with_abstract = [(i, pub) for i, pub in enumerate(publications) if pub.abstract]
    if len(with_abstract) < 2:
        return []

    texts = [pub.abstract for _, pub in with_abstract]
    sim_matrix = embedding_strategy.pairwise_cosine_similarity(texts)

    pairs = []
    for i in range(len(with_abstract)):
        for j in range(i + 1, len(with_abstract)):
            sim = float(sim_matrix[i, j])
            if sim > threshold:
                _, pub_a = with_abstract[i]
                _, pub_b = with_abstract[j]
                pairs.append({
                    "work_id_a": pub_a.work_id,
                    "work_id_b": pub_b.work_id,
                    "similarity": round(sim, 4),
                    "title_a": pub_a.title,
                    "title_b": pub_b.title,
                })

    return sorted(pairs, key=lambda p: p["similarity"], reverse=True)


def _find_publication_series(
    publications: list[Publication],
    interval_days: int = 30,
    title_similarity_threshold: float = 0.6,
) -> list[dict]:
    """Find sequences of papers published within short intervals with similar titles."""
    # Filter publications with dates and titles
    dated = [(pub, pub.publication_date) for pub in publications if pub.publication_date and pub.title]
    if len(dated) < 2:
        return []

    # Sort by date
    dated.sort(key=lambda x: x[1])

    pairs = []
    for i in range(len(dated)):
        for j in range(i + 1, len(dated)):
            pub_a, date_a = dated[i]
            pub_b, date_b = dated[j]

            delta = abs((date_b - date_a).days)
            if delta > interval_days:
                # Since sorted, all subsequent pairs will have larger delta
                break

            # Check title similarity (Jaccard on word sets)
            sim = _title_jaccard(pub_a.title, pub_b.title)
            if sim >= title_similarity_threshold:
                pairs.append({
                    "work_id_a": pub_a.work_id,
                    "work_id_b": pub_b.work_id,
                    "interval_days": delta,
                    "title_similarity": round(sim, 4),
                    "title_a": pub_a.title,
                    "title_b": pub_b.title,
                })

    return pairs


def _title_jaccard(title_a: str | None, title_b: str | None) -> float:
    """Compute Jaccard similarity between two titles based on word sets."""
    if not title_a or not title_b:
        return 0.0
    words_a = set(title_a.lower().split())
    words_b = set(title_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
