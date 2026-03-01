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
    """
    total = len(author_data.citations)
    if total == 0:
        return IndicatorResult("RLA", 0.0, {"status": "no_citations"})

    # Self-reference rate
    self_cits = sum(1 for c in author_data.citations if c.is_self_citation)
    self_ref_rate = self_cits / total

    # Reference concentration (Herfindahl index of source authors)
    source_counts: Counter[int | None] = Counter()
    non_self = 0
    for c in author_data.citations:
        if not c.is_self_citation and c.source_author_id:
            source_counts[c.source_author_id] += 1
            non_self += 1

    if non_self == 0:
        # All self-citations → max anomaly
        concentration = 1.0
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


def compute_gic(author_data: AuthorData) -> IndicatorResult:
    """Geographic/Institutional Clustering via Shannon entropy of citing sources.

    Low entropy = citations come from few unique sources = suspicious.
    Normalized so that GIC ∈ [0, 1], where 1 = maximally suspicious (lowest entropy).
    """
    # Collect source institutions/affiliations from citations
    source_affiliations: list[str] = []
    for c in author_data.citations:
        if c.is_self_citation:
            continue
        # Use source_author_id as proxy for "source" clustering
        if c.source_author_id:
            source_affiliations.append(str(c.source_author_id))

    if len(source_affiliations) < 2:
        return IndicatorResult("GIC", 0.0, {"status": "insufficient_sources"})

    # Shannon entropy of source distribution
    counts = Counter(source_affiliations)
    total = len(source_affiliations)
    entropy = -sum((n / total) * math.log2(n / total) for n in counts.values() if n > 0)

    # Max entropy = log2(unique_sources)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0

    # Normalized entropy [0, 1], inverted so low entropy = high GIC
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    gic_value = 1.0 - normalized_entropy  # invert: 0 = diverse, 1 = concentrated

    return IndicatorResult(
        "GIC",
        round(gic_value, 6),
        {
            "entropy": round(entropy, 4),
            "max_entropy": round(max_entropy, 4),
            "normalized_entropy": round(normalized_entropy, 4),
            "unique_sources": len(counts),
            "total_non_self_citations": total,
        },
    )
