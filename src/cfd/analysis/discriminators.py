"""Discriminative indicators based on OpenAlex data patterns.

These indicators exploit metrics that are well-covered by OpenAlex and show
strong discrimination between legitimate and manipulative citation profiles:
- CDF: Citation Distribution Flatness (Gini coefficient)
- HIA: h-Index Anomaly (h/works ratio vs Hirsch expectation)
- CCL: Citation Collapse (rapid post-peak decline)
- LRHC: Low-Reference High-Citation anomaly
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np

from cfd.analysis.baselines import DisciplineBaseline
from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult

logger = logging.getLogger(__name__)


def _gini_coefficient(sorted_values: list[float]) -> float:
    """Compute Gini coefficient from a sorted list of non-negative values.

    Returns 0.0 for perfect equality, approaching 1.0 for perfect inequality.
    Normal citation distributions have Gini ~0.4-0.7.
    Manipulated (flat) distributions have Gini < 0.3.
    """
    n = len(sorted_values)
    if n == 0:
        return 0.0
    total = sum(sorted_values)
    if total == 0:
        return 0.0
    cumulative = 0.0
    weighted_sum = 0.0
    for i, val in enumerate(sorted_values):
        cumulative += val
        weighted_sum += (2 * (i + 1) - n - 1) * val
    return weighted_sum / (n * total)


def _extract_yearly_citations(author_data: AuthorData) -> Counter:
    """Extract total citation counts by year from publication raw data."""
    yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.raw_data:
            for entry in pub.raw_data.get("counts_by_year", []):
                year = entry.get("year")
                cited = entry.get("cited_by_count", 0)
                if year is not None:
                    yearly[year] += cited
    return yearly


def _extract_yearly_works(author_data: AuthorData) -> Counter:
    """Extract publication counts by year."""
    yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.publication_date:
            yearly[pub.publication_date.year] += 1
    return yearly


# ---------------------------------------------------------------------------
# CDF — Citation Distribution Flatness
# ---------------------------------------------------------------------------

def compute_cdf(author_data: AuthorData) -> IndicatorResult:
    """Citation Distribution Flatness: detect unnaturally uniform citation counts.

    Natural citation distributions follow a power law (few papers with many
    citations, most with few). Manipulated profiles show artificially flat
    distributions where many papers have similar citation counts.

    Uses Gini coefficient (inverted) + coefficient of variation of top papers.
    """
    counts = sorted(
        [pub.citation_count for pub in author_data.publications if pub.citation_count > 0]
    )

    if len(counts) < 5:
        return IndicatorResult("CDF", 0.0, {"status": "insufficient_data", "cited_papers": len(counts)})

    # Component 1: Gini coefficient (inverted — low Gini = flat = suspicious)
    gini = _gini_coefficient(counts)
    # Normal: 0.4-0.7, Suspicious: < 0.3
    gini_score = max(0.0, min((0.5 - gini) / 0.5, 1.0))

    # Component 2: CV of top-10 most cited papers
    top_n = sorted(counts, reverse=True)[:min(10, len(counts))]
    arr = np.array(top_n, dtype=float)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr))
    cv = std_val / mean_val if mean_val > 0 else 0.0
    # Normal CV for top-10: 0.5-1.5. Suspicious (flat): < 0.3
    cv_score = max(0.0, min((0.5 - cv) / 0.5, 1.0))

    # Combine: 60% Gini + 40% CV
    value = 0.6 * gini_score + 0.4 * cv_score
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        "CDF",
        round(value, 4),
        {
            "gini_coefficient": round(gini, 4),
            "gini_score": round(gini_score, 4),
            "top_n_cv": round(cv, 4),
            "cv_score": round(cv_score, 4),
            "cited_papers": len(counts),
            "top_10_citations": top_n,
        },
    )


# ---------------------------------------------------------------------------
# HIA — h-Index Anomaly
# ---------------------------------------------------------------------------

def compute_hia(author_data: AuthorData, baseline: DisciplineBaseline) -> IndicatorResult:
    """h-Index Anomaly: detect disproportionately high h-index.

    Compares actual h-index to expected h using Hirsch's formula:
    h_expected ≈ 0.54 * sqrt(total_citations).

    Also checks i10/works ratio (fraction of papers with 10+ citations).
    """
    h = author_data.profile.h_index
    works = author_data.profile.publication_count
    citations = author_data.profile.citation_count

    if not h or not works or works < 5:
        return IndicatorResult("HIA", 0.0, {"status": "insufficient_data"})

    # Component 1: h-index vs Hirsch expectation
    # Hirsch (2005): h ≈ 0.54 * sqrt(C) where C = total citations
    total_cit = citations or 0
    h_expected = 0.54 * (total_cit ** 0.5) if total_cit > 0 else 1.0
    excess = max(h - h_expected, 0.0) / max(h_expected, 1.0)
    excess_score = min(excess / 1.0, 1.0)

    # Component 2: i10/works ratio
    # What fraction of papers have 10+ citations? Normal: 5-15%. Suspicious: > 30%
    i10 = sum(1 for p in author_data.publications if p.citation_count >= 10)
    i10_ratio = i10 / works
    i10_score = min(i10_ratio / 0.30, 1.0)

    # Component 3: h/works ratio
    # Normal: 0.05-0.15. Suspicious: > 0.25
    h_works_ratio = h / works
    h_works_score = max(0.0, min((h_works_ratio - 0.15) / 0.15, 1.0))

    # Combine: 40% excess + 30% i10 + 30% h/works
    value = 0.40 * excess_score + 0.30 * i10_score + 0.30 * h_works_score
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        "HIA",
        round(value, 4),
        {
            "h_index": h,
            "h_expected": round(h_expected, 2),
            "excess_ratio": round(excess, 4),
            "i10_count": i10,
            "i10_ratio": round(i10_ratio, 4),
            "h_works_ratio": round(h_works_ratio, 4),
            "works_count": works,
            "total_citations": total_cit,
        },
    )


# ---------------------------------------------------------------------------
# CCL — Citation Collapse
# ---------------------------------------------------------------------------

def compute_ccl(author_data: AuthorData) -> IndicatorResult:
    """Citation Collapse: detect rapid post-peak citation decline.

    When a citation ring stops, citations drop abruptly. Natural citation
    decay is gradual (10-20% per year). Suspicious collapse: >70% in 2 years.

    Also considers whether the peak was anomalously high for the number of
    works published that year (peak intensity).
    """
    yearly_cit = _extract_yearly_citations(author_data)

    if len(yearly_cit) < 4:
        return IndicatorResult("CCL", 0.0, {"status": "insufficient_data", "years": len(yearly_cit)})

    # Find peak
    years = sorted(yearly_cit.keys())
    peak_year = max(yearly_cit, key=yearly_cit.get)
    peak_value = yearly_cit[peak_year]

    # Need meaningful peak (at least 20 citations)
    if peak_value < 20:
        return IndicatorResult("CCL", 0.0, {
            "status": "low_peak",
            "peak_year": peak_year,
            "peak_citations": peak_value,
        })

    # Must have data after peak
    years_after_peak = sorted(y for y in years if y > peak_year)
    if not years_after_peak:
        return IndicatorResult("CCL", 0.0, {
            "status": "no_post_peak_data",
            "peak_year": peak_year,
            "peak_citations": peak_value,
        })

    # Component 1: Collapse rate (average of 1-3 years after peak vs peak)
    post_peak_years = years_after_peak[:3]
    post_peak_values = [yearly_cit.get(y, 0) for y in post_peak_years]
    avg_post = sum(post_peak_values) / len(post_peak_values)
    collapse_rate = 1.0 - avg_post / peak_value

    # Natural decay: ~15% per year = ~40% over 3 years → collapse_rate ~0.40
    # Suspicious: > 0.80 (dropped > 80%)
    collapse_score = max(0.0, min((collapse_rate - 0.40) / 0.50, 1.0))

    # Component 2: Peak intensity (citations per work in peak year)
    yearly_works = _extract_yearly_works(author_data)
    works_in_peak = yearly_works.get(peak_year, 1)
    peak_intensity = peak_value / max(works_in_peak, 1)
    # Normal: 3-8 cit/work. Suspicious: > 12
    intensity_score = max(0.0, min((peak_intensity - 8.0) / 8.0, 1.0))

    # Component 3: Consecutive decline (each year lower than previous)
    decline_years = 0
    prev = peak_value
    for y in years_after_peak[:3]:
        val = yearly_cit.get(y, 0)
        if val < prev * 0.5:  # dropped more than 50%
            decline_years += 1
        prev = val
    consecutive_score = min(decline_years / 2.0, 1.0)

    # Combine: 50% collapse + 25% intensity + 25% consecutive
    value = 0.50 * collapse_score + 0.25 * intensity_score + 0.25 * consecutive_score
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        "CCL",
        round(value, 4),
        {
            "peak_year": peak_year,
            "peak_citations": peak_value,
            "peak_works": works_in_peak,
            "peak_intensity": round(peak_intensity, 2),
            "post_peak_values": {str(y): yearly_cit.get(y, 0) for y in post_peak_years},
            "collapse_rate": round(collapse_rate, 4),
            "consecutive_decline_years": decline_years,
        },
    )


# ---------------------------------------------------------------------------
# LRHC — Low-Reference High-Citation
# ---------------------------------------------------------------------------

def compute_lrhc(author_data: AuthorData) -> IndicatorResult:
    """Low-Reference High-Citation: detect papers with few references but many citations.

    Papers with very few references are not well-integrated into the scientific
    literature. If they still receive many citations, this is anomalous and
    may indicate artificial citation boosting.
    """
    anomalies = []
    total_cited = 0

    for pub in author_data.publications:
        refs = len(pub.references_list)
        cites = pub.citation_count

        if cites < 5:
            continue
        total_cited += 1

        if refs <= 5:  # very few references
            ratio = cites / max(refs, 1)
            anomalies.append({
                "work_id": pub.work_id,
                "refs": refs,
                "cites": cites,
                "ratio": round(ratio, 2),
            })

    if total_cited == 0:
        return IndicatorResult("LRHC", 0.0, {"status": "no_cited_papers"})

    if not anomalies:
        return IndicatorResult("LRHC", 0.0, {
            "status": "no_anomalies",
            "total_cited_papers": total_cited,
        })

    # Component 1: fraction of anomalous papers
    anomaly_fraction = len(anomalies) / total_cited

    # Component 2: severity (average cites/refs ratio)
    ratios = [a["ratio"] for a in anomalies]
    avg_ratio = sum(ratios) / len(ratios)
    severity = min(avg_ratio / 10.0, 1.0)

    # Combine: 50% fraction + 50% severity
    value = 0.5 * anomaly_fraction + 0.5 * severity
    value = min(max(value, 0.0), 1.0)

    return IndicatorResult(
        "LRHC",
        round(value, 4),
        {
            "anomalous_papers": len(anomalies),
            "total_cited_papers": total_cited,
            "anomaly_fraction": round(anomaly_fraction, 4),
            "avg_ratio": round(avg_ratio, 2),
            "top_anomalies": sorted(anomalies, key=lambda a: a["ratio"], reverse=True)[:5],
        },
    )
