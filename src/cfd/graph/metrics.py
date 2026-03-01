"""Graph-based indicator computations: SCR, MCR, CB, TA, HTA, degree centrality."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date

import networkx as nx
import numpy as np

from cfd.data.models import AuthorData, Citation

logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Result of a single indicator computation."""

    indicator_type: str
    value: float
    details: dict

    def to_dict(self) -> dict:
        return asdict(self)


def compute_scr(author_data: AuthorData) -> IndicatorResult:
    """Self-Citation Ratio: SCR = |self_cit(a)| / |total_cit(a)|"""
    total = len(author_data.citations)
    if total == 0:
        return IndicatorResult("SCR", 0.0, {"self_citations": 0, "total_citations": 0})

    self_cits = sum(1 for c in author_data.citations if c.is_self_citation)
    return IndicatorResult(
        "SCR",
        self_cits / total,
        {"self_citations": self_cits, "total_citations": total},
    )


def compute_mcr(
    citations_a: list[Citation],
    citations_b: list[Citation],
    author_a_id: int,
    author_b_id: int,
) -> IndicatorResult:
    """Mutual Citation Ratio between two authors.

    MCR(a,b) = 2 * min(cit(a->b), cit(b->a)) / (|cit(a)| + |cit(b)|)
    """
    a_cites_b = sum(
        1
        for c in citations_a
        if c.source_author_id == author_a_id and c.target_author_id == author_b_id
    )
    b_cites_a = sum(
        1
        for c in citations_b
        if c.source_author_id == author_b_id and c.target_author_id == author_a_id
    )
    mutual = min(a_cites_b, b_cites_a)
    total = len(citations_a) + len(citations_b)

    if total == 0:
        return IndicatorResult("MCR", 0.0, {"pair": [author_a_id, author_b_id]})

    value = (2 * mutual) / total
    return IndicatorResult(
        "MCR",
        value,
        {
            "pair": [author_a_id, author_b_id],
            "a_cites_b": a_cites_b,
            "b_cites_a": b_cites_a,
            "mutual": mutual,
        },
    )


def compute_mcr_from_author_data(author_data: AuthorData) -> IndicatorResult:
    """Compute max MCR for the analyzed author based on available citation data.

    Finds the top citing author and computes MCR with them.
    """
    # Count citations from each source author
    source_author_counts: Counter = Counter()
    for c in author_data.citations:
        if c.source_author_id and not c.is_self_citation:
            source_author_counts[c.source_author_id] += 1

    if not source_author_counts:
        return IndicatorResult("MCR", 0.0, {"status": "no_citing_authors"})

    # Find top citing author
    top_author_id, top_count = source_author_counts.most_common(1)[0]

    # Count how many times our author cites the top citing author
    our_cites_them = sum(
        1 for c in author_data.citations if c.target_author_id == top_author_id and not c.is_self_citation
    )

    total_our = len(author_data.citations)
    total_them = top_count  # only what we know from incoming citations

    if total_our + total_them == 0:
        return IndicatorResult("MCR", 0.0, {"status": "no_data"})

    mutual = min(our_cites_them, top_count)
    value = (2 * mutual) / (total_our + total_them)

    return IndicatorResult(
        "MCR",
        value,
        {
            "top_citing_author_id": top_author_id,
            "they_cite_us": top_count,
            "we_cite_them": our_cites_them,
            "mutual": mutual,
        },
    )


def compute_cb(author_data: AuthorData) -> IndicatorResult:
    """Citation Bottleneck: CB = max_k(incoming from k) / total_incoming."""
    source_counts: Counter = Counter()
    total_incoming = 0

    for c in author_data.citations:
        if not c.is_self_citation and c.source_author_id:
            source_counts[c.source_author_id] += 1
            total_incoming += 1

    if total_incoming == 0:
        return IndicatorResult("CB", 0.0, {"max_source": None, "total_incoming": 0})

    max_source_id, max_count = source_counts.most_common(1)[0]
    value = max_count / total_incoming

    return IndicatorResult(
        "CB",
        value,
        {
            "max_source_author_id": max_source_id,
            "max_source_count": max_count,
            "total_incoming": total_incoming,
        },
    )


def compute_ta(author_data: AuthorData) -> IndicatorResult:
    """Temporal Anomaly: detect citation spikes using Z-score analysis.

    Aggregates citations by year and checks for spikes > z_threshold sigma
    from the rolling mean.
    """
    # Collect all citation dates
    citation_dates: list[date] = []
    for c in author_data.citations:
        if c.citation_date:
            citation_dates.append(c.citation_date)

    # Also check counts_by_year from raw publication data
    if not citation_dates:
        # Try to use counts_by_year from publications
        yearly_counts = _extract_counts_by_year(author_data)
        if not yearly_counts:
            return IndicatorResult("TA", 0.0, {"status": "N/A", "reason": "no_timestamps"})
    else:
        yearly_counts = Counter(d.year for d in citation_dates)

    if len(yearly_counts) < 3:
        return IndicatorResult("TA", 0.0, {"status": "N/A", "reason": "insufficient_temporal_data"})

    # Compute Z-scores for each year
    years = sorted(yearly_counts.keys())
    values = np.array([yearly_counts[y] for y in years], dtype=float)
    mean = np.mean(values)
    std = np.std(values)

    if std == 0:
        return IndicatorResult("TA", 0.0, {"status": "no_variance", "years": dict(yearly_counts)})

    z_scores = {y: (yearly_counts[y] - mean) / std for y in years}
    max_z_year = max(z_scores, key=z_scores.get)  # type: ignore[arg-type]
    max_z = z_scores[max_z_year]

    # Normalize to [0, 1]: z=3 -> 0.5, z=6 -> 1.0
    normalized = min(max(max_z / 6.0, 0.0), 1.0)

    return IndicatorResult(
        "TA",
        normalized,
        {
            "max_z_score": round(max_z, 3),
            "spike_year": max_z_year,
            "yearly_counts": {str(y): int(yearly_counts[y]) for y in years},
            "mean": round(mean, 2),
            "std": round(std, 2),
        },
    )


def _extract_counts_by_year(author_data: AuthorData) -> Counter:
    """Extract citation counts by year from publication raw data (OpenAlex counts_by_year)."""
    yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.raw_data:
            for entry in pub.raw_data.get("counts_by_year", []):
                year = entry.get("year")
                cited = entry.get("cited_by_count", 0)
                if year and cited:
                    yearly[year] += cited
    return yearly


def compute_hta(author_data: AuthorData) -> IndicatorResult:
    """h-Index Temporal Analysis: analyze h(t) growth rate.

    Uses counts_by_year to approximate h-index over time and detect
    anomalous growth.
    """
    yearly_counts = _extract_counts_by_year(author_data)
    if len(yearly_counts) < 3:
        return IndicatorResult("HTA", 0.0, {"status": "N/A", "reason": "insufficient_temporal_data"})

    # Sort by year
    years = sorted(yearly_counts.keys())
    values = [yearly_counts[y] for y in years]

    # Compute year-over-year growth rates
    growth_rates = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            growth_rates.append((values[i] - values[i - 1]) / values[i - 1])
        else:
            growth_rates.append(0.0)

    if not growth_rates:
        return IndicatorResult("HTA", 0.0, {"status": "N/A", "reason": "no_growth_data"})

    growth_arr = np.array(growth_rates)
    mean_growth = float(np.mean(growth_arr))
    std_growth = float(np.std(growth_arr))

    # Detect anomalous growth
    max_growth = float(np.max(growth_arr))
    max_z = (max_growth - mean_growth) / std_growth if std_growth > 0 else 0.0

    # Normalize to [0, 1]
    normalized = min(max(max_z / 6.0, 0.0), 1.0)

    return IndicatorResult(
        "HTA",
        normalized,
        {
            "mean_growth_rate": round(mean_growth, 3),
            "max_growth_rate": round(max_growth, 3),
            "max_z_score": round(max_z, 3),
            "years_analyzed": len(years),
        },
    )


def compute_degree_centrality(g: nx.DiGraph, node_id: str) -> tuple[IndicatorResult, IndicatorResult]:
    """In-degree and out-degree centrality for a node."""
    in_deg = g.in_degree(node_id) if node_id in g else 0
    out_deg = g.out_degree(node_id) if node_id in g else 0
    n = len(g.nodes)
    in_centrality = in_deg / (n - 1) if n > 1 else 0.0
    out_centrality = out_deg / (n - 1) if n > 1 else 0.0

    return (
        IndicatorResult(
            "degree_centrality_in",
            in_centrality,
            {"in_degree": in_deg, "total_nodes": n},
        ),
        IndicatorResult(
            "degree_centrality_out",
            out_centrality,
            {"out_degree": out_deg, "total_nodes": n},
        ),
    )
