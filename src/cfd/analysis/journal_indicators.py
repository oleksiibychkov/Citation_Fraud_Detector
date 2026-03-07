"""Journal-level citation manipulation indicators."""

from __future__ import annotations

import logging
import math
from collections import Counter
from datetime import date

import numpy as np

from cfd.data.journal_models import JournalData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def compute_j_scr(journal_data: JournalData) -> IndicatorResult:
    """Journal Self-Citation Ratio: fraction of citations from the same journal."""
    total = len(journal_data.citations)
    if total == 0:
        return IndicatorResult("J_SCR", 0.0, {"self_citations": 0, "total": 0})

    self_cits = sum(1 for c in journal_data.citations if c.is_self_citation)
    value = self_cits / total

    return IndicatorResult("J_SCR", value, {
        "self_citations": self_cits,
        "total_citations": total,
    })


def compute_j_mcr(journal_data: JournalData) -> IndicatorResult:
    """Journal Mutual Citation Ratio: detects mutual citation cartels between journals.

    Finds the journal with highest mutual citation exchange.
    """
    our_id = journal_data.profile.openalex_id

    # Incoming: how many times each journal cites us
    incoming: Counter[str] = Counter()
    for c in journal_data.citations:
        if c.source_journal_id and c.source_journal_id != our_id:
            incoming[c.source_journal_id] += 1

    total_incoming = sum(incoming.values())
    if total_incoming == 0:
        return IndicatorResult("J_MCR", 0.0, {"status": "no_incoming_citations"})

    # Find top citing journal
    top_journal, top_count = incoming.most_common(1)[0]
    concentration = top_count / total_incoming

    return IndicatorResult("J_MCR", concentration, {
        "top_citing_journal": top_journal,
        "top_citing_count": top_count,
        "total_incoming": total_incoming,
        "unique_citing_journals": len(incoming),
    })


def compute_j_ta(journal_data: JournalData) -> IndicatorResult:
    """Journal Temporal Anomaly: detect citation spikes in journal history."""
    counts_by_year = journal_data.profile.counts_by_year
    if len(counts_by_year) < 3:
        return IndicatorResult("J_TA", 0.0, {"status": "insufficient_data"})

    yearly = {}
    for entry in counts_by_year:
        year = entry.get("year")
        cited = entry.get("cited_by_count", 0)
        if year is not None:
            yearly[year] = cited

    if len(yearly) < 3:
        return IndicatorResult("J_TA", 0.0, {"status": "insufficient_years"})

    years = sorted(yearly.keys())
    values = np.array([yearly[y] for y in years], dtype=float)
    mean = float(np.mean(values))
    std = float(np.std(values))

    if std == 0:
        return IndicatorResult("J_TA", 0.0, {"status": "no_variance"})

    z_scores = {y: (yearly[y] - mean) / std for y in years}
    max_z_year = max(z_scores, key=z_scores.get)  # type: ignore[arg-type]
    max_z = z_scores[max_z_year]

    # Normalize: 3.0 -> 0.5, 6.0 -> 1.0
    z_threshold = 3.0
    normalized = min(max(max_z / (z_threshold * 2), 0.0), 1.0)

    return IndicatorResult("J_TA", normalized, {
        "max_z_score": round(max_z, 3),
        "spike_year": max_z_year,
        "mean_citations": round(mean, 1),
        "std_citations": round(std, 1),
        "yearly_counts": {str(y): int(yearly[y]) for y in years},
    })


def compute_j_hia(journal_data: JournalData) -> IndicatorResult:
    """Journal h-Index Anomaly: compare h-index to expected based on works/citations.

    A journal with artificially inflated h-index will have h >> sqrt(total_citations).
    """
    h_index = journal_data.profile.h_index
    if h_index is None or h_index == 0:
        return IndicatorResult("J_HIA", 0.0, {"status": "no_h_index"})

    total_cits = journal_data.profile.cited_by_count
    works_count = journal_data.profile.works_count

    if total_cits == 0 or works_count == 0:
        return IndicatorResult("J_HIA", 0.0, {"status": "no_data"})

    # Expected h-index approximation: h ~ sqrt(total_citations) for honest distribution
    expected_h = math.sqrt(total_cits)
    # Also consider works count: h can't exceed works_count
    avg_cits = total_cits / works_count

    # Ratio of actual to expected
    ratio = h_index / expected_h if expected_h > 0 else 0

    # If h-index is suspiciously high relative to expected
    # Normal ratio is ~0.5-1.5; >2.0 is suspicious
    anomaly = max(0.0, (ratio - 1.5) / 1.5)
    anomaly = min(anomaly, 1.0)

    return IndicatorResult("J_HIA", anomaly, {
        "h_index": h_index,
        "expected_h": round(expected_h, 1),
        "ratio": round(ratio, 3),
        "total_citations": total_cits,
        "works_count": works_count,
        "avg_citations_per_work": round(avg_cits, 2),
    })


def compute_j_cdf(journal_data: JournalData) -> IndicatorResult:
    """Journal Citation Distribution Fairness: detect abnormal concentration.

    In a healthy journal, citations follow a power law. If too many papers
    have similar citation counts (too uniform), it suggests manipulation.
    """
    if not journal_data.works:
        return IndicatorResult("J_CDF", 0.0, {"status": "no_works"})

    citations = [w.cited_by_count for w in journal_data.works]
    if not citations or max(citations) == 0:
        return IndicatorResult("J_CDF", 0.0, {"status": "no_citations"})

    total = sum(citations)
    n = len(citations)

    # Gini coefficient: 0 = perfect equality, 1 = maximum inequality
    sorted_cits = sorted(citations)
    cumulative = np.cumsum(sorted_cits)
    gini = 1 - 2 * np.sum(cumulative) / (n * total) + 1 / n if total > 0 else 0

    # For journals: too LOW Gini (too equal) is suspicious
    # Normal journals have Gini ~0.5-0.8 (power law)
    # Manipulated journals might have Gini < 0.3
    if gini < 0.3:
        anomaly = (0.3 - gini) / 0.3  # Lower Gini = more suspicious
    else:
        anomaly = 0.0

    # Also check: what % of papers have zero citations
    zero_pct = sum(1 for c in citations if c == 0) / n

    # Combine: uniform distribution (60%) + high zero rate (40%)
    # High zero rate with some very cited papers = normal
    # Low zero rate with uniform citations = suspicious
    uniform_signal = anomaly
    zero_signal = max(0.0, 0.3 - zero_pct) / 0.3 if zero_pct < 0.3 else 0.0

    value = 0.6 * uniform_signal + 0.4 * zero_signal
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult("J_CDF", value, {
        "gini_coefficient": round(float(gini), 4),
        "zero_citation_pct": round(zero_pct, 4),
        "total_works_analyzed": n,
        "mean_citations": round(float(np.mean(citations)), 2),
        "median_citations": round(float(np.median(citations)), 2),
        "max_citations": int(max(citations)),
    })


def compute_j_coerce(journal_data: JournalData) -> IndicatorResult:
    """Journal Coercive Citation: detect if journal forces authors to cite its papers.

    Signal: high self-citation ratio combined with citations appearing in
    recently published papers (suggesting editorial pressure).
    """
    if not journal_data.citations:
        return IndicatorResult("J_COERCE", 0.0, {"status": "no_citations"})

    # Check references in journal's own works pointing back to same journal
    total_refs = 0
    self_refs = 0
    work_ids_in_journal = {w.work_id for w in journal_data.works}
    for work in journal_data.works:
        for ref in work.references_list:
            total_refs += 1
            if ref in work_ids_in_journal:
                self_refs += 1

    if total_refs == 0:
        return IndicatorResult("J_COERCE", 0.0, {"status": "no_references"})

    # Self-reference ratio (papers in journal citing other papers in same journal)
    self_ref_ratio = self_refs / total_refs

    # Check concentration in recent years (editorial pressure signal)
    recent_self_cits = 0
    total_recent = 0
    for c in journal_data.citations:
        if c.citation_date and c.citation_date.year >= date.today().year - 2:
            total_recent += 1
            if c.is_self_citation:
                recent_self_cits += 1

    recent_self_ratio = recent_self_cits / total_recent if total_recent > 0 else 0

    # Coercive signal: high self-ref + increasing trend
    value = 0.5 * min(self_ref_ratio / 0.3, 1.0) + 0.5 * min(recent_self_ratio / 0.3, 1.0)
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult("J_COERCE", value, {
        "self_reference_ratio": round(self_ref_ratio, 4),
        "total_references": total_refs,
        "self_references": self_refs,
        "recent_self_citation_ratio": round(recent_self_ratio, 4),
        "recent_total": total_recent,
    })


def compute_j_ec(journal_data: JournalData) -> IndicatorResult:
    """Editorial Concentration: detect if few authors dominate the journal.

    High concentration of authorship suggests potential editorial manipulation.
    """
    if not journal_data.works:
        return IndicatorResult("J_EC", 0.0, {"status": "no_works"})

    author_counts: Counter[str] = Counter()
    for work in journal_data.works:
        for author in work.authors:
            aid = author.get("author_id", "")
            if aid:
                author_counts[aid] += 1

    if not author_counts:
        return IndicatorResult("J_EC", 0.0, {"status": "no_authors"})

    total_authorships = sum(author_counts.values())
    unique_authors = len(author_counts)

    # Top 10 authors' share
    top_10 = author_counts.most_common(10)
    top_10_count = sum(c for _, c in top_10)
    top_10_share = top_10_count / total_authorships

    # Herfindahl index for author concentration
    hhi = sum((c / total_authorships) ** 2 for c in author_counts.values())

    # Anomaly: top 10 authors contributing >40% of papers is suspicious
    value = min(max((top_10_share - 0.2) / 0.4, 0.0), 1.0)

    return IndicatorResult("J_EC", value, {
        "unique_authors": unique_authors,
        "total_authorships": total_authorships,
        "top_10_share": round(top_10_share, 4),
        "herfindahl_index": round(hhi, 6),
        "top_author_papers": top_10[0][1] if top_10 else 0,
    })


def compute_j_cb(journal_data: JournalData) -> IndicatorResult:
    """Journal Citation Bottleneck: fraction of citations from top citing journal."""
    citing = journal_data.citing_journals
    our_id = journal_data.profile.openalex_id

    # Exclude self-citations
    external = {k: v for k, v in citing.items() if k != our_id}
    if not external:
        return IndicatorResult("J_CB", 0.0, {"status": "no_external_citations"})

    total = sum(external.values())
    top_journal = max(external, key=external.get)  # type: ignore[arg-type]
    top_count = external[top_journal]
    concentration = top_count / total

    return IndicatorResult("J_CB", concentration, {
        "top_citing_journal": top_journal,
        "top_count": top_count,
        "total_external": total,
        "unique_citing_journals": len(external),
    })


def compute_j_growth(journal_data: JournalData) -> IndicatorResult:
    """Journal Growth Anomaly: detect unnatural growth in works/citations.

    Sudden jumps in publication volume or citation count suggest manipulation.
    """
    counts = journal_data.profile.counts_by_year
    if len(counts) < 3:
        return IndicatorResult("J_GROWTH", 0.0, {"status": "insufficient_data"})

    yearly_works = {}
    yearly_cits = {}
    for entry in counts:
        year = entry.get("year")
        if year is not None:
            yearly_works[year] = entry.get("works_count", 0)
            yearly_cits[year] = entry.get("cited_by_count", 0)

    if len(yearly_works) < 3:
        return IndicatorResult("J_GROWTH", 0.0, {"status": "insufficient_years"})

    years = sorted(yearly_works.keys())
    work_values = [yearly_works[y] for y in years]

    # Year-over-year growth rates for works
    growth_rates = []
    for i in range(1, len(work_values)):
        if work_values[i - 1] > 0:
            growth_rates.append((work_values[i] - work_values[i - 1]) / work_values[i - 1])
        elif work_values[i] > 0:
            growth_rates.append(1.0)

    if not growth_rates:
        return IndicatorResult("J_GROWTH", 0.0, {"status": "no_growth_data"})

    arr = np.array(growth_rates)
    mean_growth = float(np.mean(arr))
    max_growth = float(np.max(arr))
    std_growth = float(np.std(arr))

    # Z-score of max growth
    max_z = (max_growth - mean_growth) / std_growth if std_growth > 0 else 0
    normalized = min(max(max_z / 6.0, 0.0), 1.0)

    return IndicatorResult("J_GROWTH", normalized, {
        "max_growth_rate": round(max_growth, 3),
        "mean_growth_rate": round(mean_growth, 3),
        "max_z_score": round(max_z, 3),
        "years_analyzed": len(years),
    })
