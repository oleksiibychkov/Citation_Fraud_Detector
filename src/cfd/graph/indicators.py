"""New Stage 2 indicators: RLA (Reference List Anomaly) and GIC (Geographic/Institutional Clustering)."""

from __future__ import annotations

import math
from collections import Counter

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult


def compute_rla(author_data: AuthorData) -> IndicatorResult:
    """Reference List Anomaly: combines self-reference rate with reference concentration.

    RLA = 0.5 * self_ref_rate + 0.5 * reference_concentration

    - self_ref_rate: fraction of citations that are self-citations
    - reference_concentration: Herfindahl index of citing sources
      (high concentration = few sources = suspicious)

    Uses source_author_id when populated, with fallback to work-to-author derivation.
    """
    author_work_ids = {pub.work_id for pub in author_data.publications}
    total = len(author_data.citations)
    if total == 0:
        return IndicatorResult("RLA", 0.0, {"status": "no_citations"})

    # Self-reference rate
    self_cits = sum(1 for c in author_data.citations if c.is_self_citation)
    self_ref_rate = self_cits / total

    # Reference concentration (Herfindahl index of citing sources)
    source_counts: Counter[str] = Counter()
    non_self = 0

    # Try source_author_id first (populated by OpenAlex _fetch_citing_works)
    for c in author_data.citations:
        if not c.is_self_citation and c.source_author_id:
            # If we have publications, only count incoming citations
            if author_work_ids and c.target_work_id not in author_work_ids:
                continue
            source_counts[c.source_author_id] += 1
            non_self += 1

    # Fallback: derive from work-to-author mapping
    if non_self == 0:
        source_counts, non_self = _derive_source_counts(author_data)

    if non_self == 0:
        # No incoming citations at all (not counting self) — cannot determine concentration
        # Use only self-citation component
        concentration = 0.0
        value = self_ref_rate  # Only self-ref component
    else:
        hhi = sum((count / non_self) ** 2 for count in source_counts.values())
        # Normalize: min HHI = 1/n_sources, max = 1.0
        n_sources = len(source_counts)
        min_hhi = 1.0 / n_sources if n_sources > 0 else 1.0
        concentration = (hhi - min_hhi) / (1.0 - min_hhi) if min_hhi < 1.0 else hhi
        value = 0.5 * self_ref_rate + 0.5 * concentration

    return IndicatorResult(
        "RLA",
        round(value, 6),
        {
            "self_ref_rate": round(self_ref_rate, 4),
            "reference_concentration": round(concentration, 4),
            "self_citations": self_cits,
            "unique_sources": len(source_counts),
            "total_citations": total,
        },
    )


def _derive_source_counts(author_data: AuthorData) -> tuple[Counter[str], int]:
    """Derive citing source author counts from work-level citations via co_authors."""
    our_id = author_data.profile.openalex_id
    author_work_ids = {pub.work_id for pub in author_data.publications}

    work_to_authors: dict[str, set[str]] = {}
    for pub in author_data.publications:
        authors = set()
        for ca in pub.co_authors:
            aid = ca.get("author_id", "")
            if aid:
                authors.add(aid)
        if authors:
            work_to_authors[pub.work_id] = authors

    source_counts: Counter[str] = Counter()
    non_self = 0

    for c in author_data.citations:
        if c.is_self_citation:
            continue
        if c.target_work_id not in author_work_ids:
            continue
        src_authors = work_to_authors.get(c.source_work_id, set())
        for sa in src_authors:
            if sa != our_id:
                source_counts[sa] += 1
                non_self += 1

    return source_counts, non_self


def compute_gic(author_data: AuthorData) -> IndicatorResult:
    """Geographic/Institutional Clustering via Shannon entropy of citing sources.

    Low entropy = citations come from few unique institutions = suspicious.
    Normalized so that GIC ∈ [0, 1], where 1 = maximally suspicious (lowest entropy).

    Uses source_institution when available, falls back to source_author_id,
    then to work-to-author derivation.
    """
    author_work_ids = {pub.work_id for pub in author_data.publications}
    our_institution = (author_data.profile.institution or "").strip().lower()

    # Collect source institutions from incoming citations
    source_labels: list[str] = []
    same_institution_count = 0

    for c in author_data.citations:
        if c.is_self_citation:
            continue
        # If we have publications, only count incoming citations
        if author_work_ids and c.target_work_id not in author_work_ids:
            continue

        # Prefer institution, fallback to author ID
        label = None
        if c.source_institution:
            label = c.source_institution.strip().lower()
        elif c.source_author_id:
            label = c.source_author_id

        if label:
            source_labels.append(label)
            if c.source_institution and our_institution and label == our_institution:
                same_institution_count += 1

    # Fallback: derive from co_authors if no labels found
    if len(source_labels) < 2:
        source_labels, same_institution_count = _derive_gic_labels(
            author_data, our_institution,
        )

    if len(source_labels) < 2:
        return IndicatorResult("GIC", 0.0, {"status": "insufficient_sources"})

    # Shannon entropy of source distribution
    counts = Counter(source_labels)
    total = len(source_labels)
    entropy = -sum((n / total) * math.log2(n / total) for n in counts.values() if n > 0)

    # Max entropy = log2(unique_sources)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0

    # Normalized entropy [0, 1], inverted so low entropy = high GIC
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    gic_value = 1.0 - normalized_entropy  # invert: 0 = diverse, 1 = concentrated

    # Same-institution ratio as supplementary info
    same_inst_ratio = same_institution_count / total if total > 0 else 0.0

    return IndicatorResult(
        "GIC",
        round(gic_value, 6),
        {
            "entropy": round(entropy, 4),
            "max_entropy": round(max_entropy, 4),
            "normalized_entropy": round(normalized_entropy, 4),
            "unique_sources": len(counts),
            "total_non_self_citations": total,
            "same_institution_count": same_institution_count,
            "same_institution_ratio": round(same_inst_ratio, 4),
        },
    )


def _derive_gic_labels(
    author_data: AuthorData, our_institution: str,
) -> tuple[list[str], int]:
    """Derive GIC source labels from work-to-author mapping as fallback."""
    our_id = author_data.profile.openalex_id
    author_work_ids = {pub.work_id for pub in author_data.publications}

    work_to_authors: dict[str, set[str]] = {}
    for pub in author_data.publications:
        authors = set()
        for ca in pub.co_authors:
            aid = ca.get("author_id", "")
            if aid:
                authors.add(aid)
        if authors:
            work_to_authors[pub.work_id] = authors

    source_labels: list[str] = []
    same_institution_count = 0

    for c in author_data.citations:
        if c.is_self_citation:
            continue
        if c.target_work_id not in author_work_ids:
            continue
        src_authors = work_to_authors.get(c.source_work_id, set())
        for sa in src_authors:
            if sa != our_id:
                source_labels.append(sa)

    return source_labels, same_institution_count
