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
    author_a_id: str | int,
    author_b_id: str | int,
) -> IndicatorResult:
    """Mutual Citation Ratio between two authors.

    MCR(a,b) = 2 * min(cit(a->b), cit(b->a)) / (|cit(a)| + |cit(b)|)
    """
    # Normalize to strings for comparison (source_author_id is now str | None)
    a_id = str(author_a_id)
    b_id = str(author_b_id)

    a_cites_b = sum(
        1
        for c in citations_a
        if c.source_author_id == a_id and c.target_author_id == b_id
    )
    b_cites_a = sum(
        1
        for c in citations_b
        if c.source_author_id == b_id and c.target_author_id == a_id
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

    Derives author-to-author citation edges from work-level citations using
    co-author metadata, then finds the author pair with highest mutual citation.
    """
    our_id = author_data.profile.openalex_id

    # Build work -> authors mapping from co_authors
    work_to_authors: dict[str, set[str]] = {}
    for pub in author_data.publications:
        authors = set()
        for ca in pub.co_authors:
            aid = ca.get("author_id", "")
            if aid:
                authors.add(aid)
        if authors:
            work_to_authors[pub.work_id] = authors

    if not work_to_authors or not our_id:
        # Fallback: try legacy author-level IDs
        return _compute_mcr_legacy(author_data)

    # Derive author-to-author directed citation counts
    # For each citation (source_work -> target_work), authors of source cite authors of target
    pair_counts: Counter[tuple[str, str]] = Counter()
    author_total: Counter[str] = Counter()

    for c in author_data.citations:
        src_authors = work_to_authors.get(c.source_work_id, set())
        tgt_authors = work_to_authors.get(c.target_work_id, set())
        for sa in src_authors:
            for ta in tgt_authors:
                if sa != ta:
                    pair_counts[(sa, ta)] += 1
                    author_total[sa] += 1

    if not pair_counts:
        return IndicatorResult("MCR", 0.0, {"status": "no_author_citation_edges"})

    # Find the author with highest mutual citation with our author
    best_mcr = 0.0
    best_details: dict = {}

    # Collect all authors that cite us or we cite them
    related_authors: set[str] = set()
    for (sa, ta) in pair_counts:
        if sa == our_id:
            related_authors.add(ta)
        if ta == our_id:
            related_authors.add(sa)

    for other_id in related_authors:
        they_cite_us = pair_counts.get((other_id, our_id), 0)
        we_cite_them = pair_counts.get((our_id, other_id), 0)

        if they_cite_us == 0 or we_cite_them == 0:
            continue  # no mutual citation

        total_our = author_total.get(our_id, 0)
        total_them = author_total.get(other_id, 0)
        denom = total_our + total_them
        if denom == 0:
            continue

        mutual = min(they_cite_us, we_cite_them)
        mcr_value = (2 * mutual) / denom

        if mcr_value > best_mcr:
            best_mcr = mcr_value
            best_details = {
                "top_mutual_author_id": other_id,
                "they_cite_us": they_cite_us,
                "we_cite_them": we_cite_them,
                "mutual": mutual,
                "total_our_edges": total_our,
                "total_their_edges": total_them,
            }

    if not best_details:
        return IndicatorResult("MCR", 0.0, {"status": "no_mutual_citations"})

    return IndicatorResult("MCR", best_mcr, best_details)


def _compute_mcr_legacy(author_data: AuthorData) -> IndicatorResult:
    """Fallback MCR using legacy source_author_id / target_author_id fields."""
    source_author_counts: Counter = Counter()
    for c in author_data.citations:
        if c.source_author_id and not c.is_self_citation:
            source_author_counts[c.source_author_id] += 1

    if not source_author_counts:
        return IndicatorResult("MCR", 0.0, {"status": "no_citing_authors"})

    top_author_id, top_count = source_author_counts.most_common(1)[0]
    our_cites_them = sum(
        1 for c in author_data.citations if c.target_author_id == top_author_id and not c.is_self_citation
    )
    total_our = len(author_data.citations)
    total_them = top_count

    if total_our + total_them == 0:
        return IndicatorResult("MCR", 0.0, {"status": "no_data"})

    mutual = min(our_cites_them, top_count)
    value = (2 * mutual) / (total_our + total_them)
    return IndicatorResult("MCR", value, {
        "top_citing_author_id": top_author_id,
        "they_cite_us": top_count,
        "we_cite_them": our_cites_them,
        "mutual": mutual,
    })


def compute_cb(author_data: AuthorData) -> IndicatorResult:
    """Citation Bottleneck: CB = max_k(incoming from k) / total_incoming.

    Identifies when a disproportionate share of citations comes from a single source.
    Uses source_author_id when available (populated by OpenAlex), with fallback
    to deriving author-to-author edges from work-level citations via co_authors.
    """
    author_work_ids = {pub.work_id for pub in author_data.publications}

    # Try direct source_author_id first (populated by _fetch_citing_works)
    source_counts: Counter[str] = Counter()
    total_incoming = 0

    for c in author_data.citations:
        if not c.is_self_citation and c.source_author_id:
            # If we have publications, only count incoming citations
            if author_work_ids and c.target_work_id not in author_work_ids:
                continue
            source_counts[c.source_author_id] += 1
            total_incoming += 1

    # Fallback: derive from work-to-author mapping (same approach as MCR fix)
    if total_incoming == 0:
        source_counts, total_incoming = _derive_cb_from_works(author_data)

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
            "unique_sources": len(source_counts),
        },
    )


def _derive_cb_from_works(author_data: AuthorData) -> tuple[Counter[str], int]:
    """Derive citation bottleneck from work-level citations via co_authors.

    For each incoming citation to our publications, determine the citing authors
    from work_to_authors mapping.
    """
    our_id = author_data.profile.openalex_id
    author_work_ids = {pub.work_id for pub in author_data.publications}

    # Build work -> authors mapping
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
    total_incoming = 0

    for c in author_data.citations:
        if c.is_self_citation:
            continue
        # Only count incoming citations (where target is our publication)
        if c.target_work_id not in author_work_ids:
            continue
        # Get authors of the citing work
        src_authors = work_to_authors.get(c.source_work_id, set())
        for sa in src_authors:
            if sa != our_id:
                source_counts[sa] += 1
                total_incoming += 1

    return source_counts, total_incoming


def compute_ta(author_data: AuthorData, z_threshold: float = 3.0) -> IndicatorResult:
    """Temporal Anomaly: detect citation spikes using Z-score analysis.

    Enhanced (Stage 3): monthly granularity when available, cross-check
    with publication count to distinguish legitimate growth from anomalies.
    """
    # Collect all citation dates
    citation_dates: list[date] = []
    for c in author_data.citations:
        if c.citation_date:
            citation_dates.append(c.citation_date)

    # Also check counts_by_year from raw publication data
    if not citation_dates:
        yearly_counts = _extract_counts_by_year(author_data)
        if not yearly_counts:
            return IndicatorResult("TA", 0.0, {"status": "N/A", "reason": "no_timestamps"})
    else:
        yearly_counts = Counter(d.year for d in citation_dates)

    if len(yearly_counts) < 3:
        return IndicatorResult("TA", 0.0, {"status": "N/A", "reason": "insufficient_temporal_data"})

    # Compute yearly Z-scores
    years = sorted(yearly_counts.keys())
    values = np.array([yearly_counts[y] for y in years], dtype=float)
    mean = float(np.mean(values))
    std = float(np.std(values))

    if std == 0:
        return IndicatorResult("TA", 0.0, {"status": "no_variance", "years": dict(yearly_counts)})

    z_scores = {y: (yearly_counts[y] - mean) / std for y in years}
    max_z_year = max(z_scores, key=z_scores.get)  # type: ignore[arg-type]
    max_z = z_scores[max_z_year]

    # Monthly granularity (when citation dates are available)
    monthly_spike = None
    if citation_dates:
        monthly_counts = Counter((d.year, d.month) for d in citation_dates)
        if len(monthly_counts) >= 6:
            m_values = np.array(list(monthly_counts.values()), dtype=float)
            m_mean = float(np.mean(m_values))
            m_std = float(np.std(m_values))
            if m_std > 0:
                m_z = {k: (v - m_mean) / m_std for k, v in monthly_counts.items()}
                max_m_key = max(m_z, key=m_z.get)  # type: ignore[arg-type]
                monthly_spike = {
                    "month": f"{max_m_key[0]}-{max_m_key[1]:02d}",
                    "z_score": round(m_z[max_m_key], 3),
                }

    # Cross-check: publication count by year
    pub_yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.publication_date:
            pub_yearly[pub.publication_date.year] += 1

    citation_pub_correlation = None
    pub_adjusted = max_z
    if pub_yearly and len(pub_yearly) >= 3:
        common_years = sorted(set(years) & set(pub_yearly.keys()))
        if len(common_years) >= 3:
            cit_vals = np.array([yearly_counts[y] for y in common_years], dtype=float)
            pub_vals = np.array([pub_yearly[y] for y in common_years], dtype=float)
            if np.std(pub_vals) > 0 and np.std(cit_vals) > 0:
                corr = float(np.corrcoef(cit_vals, pub_vals)[0, 1])
                citation_pub_correlation = round(corr, 4)
                # If citations spike without publication increase, boost anomaly
                if corr < 0.3 and max_z > z_threshold:
                    pub_adjusted = max_z * 1.3

    # Normalize: z_threshold -> 0.5, z_threshold*2 -> 1.0
    normalized = min(max(pub_adjusted / (z_threshold * 2), 0.0), 1.0)

    details: dict = {
        "max_z_score": round(pub_adjusted, 3),
        "raw_max_z": round(max_z, 3),
        "spike_year": max_z_year,
        "yearly_counts": {str(y): int(yearly_counts[y]) for y in years},
        "mean": round(mean, 2),
        "std": round(std, 2),
        "z_threshold": z_threshold,
    }
    if monthly_spike:
        details["monthly_spike"] = monthly_spike
    if citation_pub_correlation is not None:
        details["citation_pub_correlation"] = citation_pub_correlation
    if pub_adjusted != max_z:
        details["pub_adjusted_z"] = round(pub_adjusted, 3)

    return IndicatorResult("TA", normalized, details)


def _extract_counts_by_year(author_data: AuthorData) -> Counter:
    """Extract citation counts by year from publication raw data (OpenAlex counts_by_year)."""
    yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.raw_data:
            for entry in pub.raw_data.get("counts_by_year", []):
                year = entry.get("year")
                cited = entry.get("cited_by_count", 0)
                if year is not None:
                    yearly[year] += cited
    return yearly


def compute_hta(author_data: AuthorData) -> IndicatorResult:
    """h-Index Temporal Analysis: analyze h(t) growth rate.

    Enhanced (Stage 3): reconstructs h(t) over time, computes dh/dt vs dN/dt
    correlation, and detects anomalous growth uncorrelated with publications.
    """
    yearly_counts = _extract_counts_by_year(author_data)
    if len(yearly_counts) < 3:
        return IndicatorResult("HTA", 0.0, {"status": "N/A", "reason": "insufficient_temporal_data"})

    years = sorted(yearly_counts.keys())
    values = [yearly_counts[y] for y in years]

    # Compute year-over-year citation growth rates
    growth_rates = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            growth_rates.append((values[i] - values[i - 1]) / values[i - 1])
        else:
            # 0→nonzero is highly anomalous; use the raw value as a proxy
            growth_rates.append(float(values[i]) if values[i] > 0 else 0.0)

    if not growth_rates:
        return IndicatorResult("HTA", 0.0, {"status": "N/A", "reason": "no_growth_data"})

    growth_arr = np.array(growth_rates)
    mean_growth = float(np.mean(growth_arr))
    std_growth = float(np.std(growth_arr))

    max_growth = float(np.max(growth_arr))
    max_z = (max_growth - mean_growth) / std_growth if std_growth > 0 else 0.0

    # Build publication count by year (N(t))
    pub_yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.publication_date:
            pub_yearly[pub.publication_date.year] += 1

    # Compute h(t) vs N(t) correlation
    h_n_correlation = None
    if pub_yearly and len(pub_yearly) >= 3:
        common_years = sorted(set(years) & set(pub_yearly.keys()))
        if len(common_years) >= 3:
            cit_vals = np.array([values[years.index(y)] for y in common_years], dtype=float)
            pub_vals = np.array([pub_yearly[y] for y in common_years], dtype=float)
            # Cumulative for h-proxy: approximate h(t) as cumulative citations / cumulative pubs
            cum_cit = np.cumsum(cit_vals)
            cum_pub = np.cumsum(pub_vals)
            if np.std(cum_pub) > 0 and np.std(cum_cit) > 0:
                corr = float(np.corrcoef(cum_cit, cum_pub)[0, 1])
                h_n_correlation = round(corr, 4)
                # Low correlation with high growth = suspicious
                effective_z = max_z * 1.2 if corr < 0.5 and max_z > 3.0 else max_z
            else:
                effective_z = max_z
        else:
            effective_z = max_z
    else:
        effective_z = max_z

    # Normalize to [0, 1] — consistent with TA (z_threshold * 2)
    z_threshold = 3.0
    normalized = min(max(effective_z / (z_threshold * 2), 0.0), 1.0)

    details: dict = {
        "mean_growth_rate": round(mean_growth, 3),
        "max_growth_rate": round(max_growth, 3),
        "max_z_score": round(effective_z, 3),
        "raw_max_z": round(max_z, 3),
        "years_analyzed": len(years),
    }
    if h_n_correlation is not None:
        details["h_n_correlation"] = h_n_correlation

    return IndicatorResult("HTA", normalized, details)


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
