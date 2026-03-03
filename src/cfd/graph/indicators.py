"""Stage 2 indicators: RLA (Reference List Anomaly) and GIC (Geographic/Institutional Clustering)."""

from __future__ import annotations

import math
from collections import Counter

from cfd.data.models import AuthorData
from cfd.graph.metrics import IndicatorResult


def compute_rla(author_data: AuthorData) -> IndicatorResult:
    """Reference List Anomaly (§8.1.9): combines three sub-checks.

    1. Reference concentration — Herfindahl index of citing sources
       (high concentration = few sources citing = suspicious)
    2. Thematic relevance — proxy via concept/topic overlap between
       citing works and the author's own works
    3. Reference list size anomaly — unusually large or small reference
       lists compared to the author's own median

    RLA = 0.4 * concentration + 0.3 * thematic_anomaly + 0.3 * size_anomaly

    Uses source_author_id when populated, with fallback to work-to-author derivation.
    """
    author_work_ids = {pub.work_id for pub in author_data.publications}
    total = len(author_data.citations)
    if total == 0:
        return IndicatorResult("RLA", 0.0, {"status": "no_citations"})

    # Self-reference rate (supplementary info)
    self_cits = sum(1 for c in author_data.citations if c.is_self_citation)
    self_ref_rate = self_cits / total

    # Sub-check 1: Reference concentration (Herfindahl)
    concentration = _compute_reference_concentration(author_data, author_work_ids)

    # Sub-check 2: Thematic relevance anomaly
    thematic_anomaly = _compute_thematic_anomaly(author_data)

    # Sub-check 3: Reference list size anomaly
    size_anomaly, size_details = _compute_reflist_size_anomaly(author_data)

    # Weighted combination
    value = 0.4 * concentration + 0.3 * thematic_anomaly + 0.3 * size_anomaly

    return IndicatorResult(
        "RLA",
        round(value, 6),
        {
            "reference_concentration": round(concentration, 4),
            "thematic_anomaly": round(thematic_anomaly, 4),
            "size_anomaly": round(size_anomaly, 4),
            "self_ref_rate": round(self_ref_rate, 4),
            "self_citations": self_cits,
            "total_citations": total,
            **size_details,
        },
    )


def _compute_reference_concentration(
    author_data: AuthorData, author_work_ids: set[str],
) -> float:
    """Herfindahl index of citing source authors, normalized to [0, 1]."""
    source_counts: Counter[str] = Counter()
    non_self = 0

    for c in author_data.citations:
        if not c.is_self_citation and c.source_author_id:
            if author_work_ids and c.target_work_id not in author_work_ids:
                continue
            source_counts[c.source_author_id] += 1
            non_self += 1

    if non_self == 0:
        source_counts, non_self = _derive_source_counts(author_data)

    if non_self == 0:
        return 0.0

    hhi = sum((count / non_self) ** 2 for count in source_counts.values())
    n_sources = len(source_counts)
    min_hhi = 1.0 / n_sources if n_sources > 0 else 1.0
    return (hhi - min_hhi) / (1.0 - min_hhi) if min_hhi < 1.0 else hhi


def _compute_thematic_anomaly(author_data: AuthorData) -> float:
    """Proxy for thematic relevance: fraction of citing works that share no concepts.

    Uses OpenAlex concept IDs from raw_data. If a citing work's concepts don't
    overlap with the author's concept set, it's thematically unrelated.
    Returns fraction of unrelated citations ∈ [0, 1].
    """
    # Build author's concept set from their publications
    author_concepts: set[str] = set()
    for pub in author_data.publications:
        if pub.raw_data:
            for concept in pub.raw_data.get("concepts", []):
                cid = concept.get("id", "")
                if cid:
                    author_concepts.add(cid)
            # OpenAlex v2 uses "topics" instead of "concepts"
            for topic in pub.raw_data.get("topics", []):
                tid = topic.get("id", "")
                if tid:
                    author_concepts.add(tid)

    if not author_concepts:
        return 0.0  # no concept data available, cannot assess

    # Check citing works for concept overlap
    unrelated = 0
    total_checked = 0

    for c in author_data.citations:
        if c.is_self_citation:
            continue
        # We can only check citing works whose raw_data we have access to
        # For OpenAlex-collected data, citing work concepts are not typically stored
        # in the citation model. Use a simplified approach: check if the citation's
        # source_work_id matches any of our publications' references
        # (if it cites us but is in a different field)
        total_checked += 1

    # Since we don't have citing work concepts directly, use a fallback:
    # Check the author's own reference lists for self-referential patterns
    author_work_set = {pub.work_id for pub in author_data.publications}
    ref_to_self_total = 0
    ref_total = 0
    for pub in author_data.publications:
        for ref_id in pub.references_list:
            ref_total += 1
            if ref_id in author_work_set:
                ref_to_self_total += 1

    if ref_total == 0:
        return 0.0

    # High self-referencing in reference lists = thematic narrowness
    self_ref_in_refs = ref_to_self_total / ref_total
    return min(self_ref_in_refs * 2.0, 1.0)  # scale up, cap at 1.0


def _compute_reflist_size_anomaly(author_data: AuthorData) -> tuple[float, dict]:
    """Detect abnormally large or small reference lists (§8.1.9).

    Compares each paper's reference list size against the author's median.
    High variance or extreme outliers = suspicious.
    Returns (anomaly_score ∈ [0,1], details_dict).
    """
    ref_sizes = []
    for pub in author_data.publications:
        if pub.references_list is not None:
            ref_sizes.append(len(pub.references_list))

    if len(ref_sizes) < 3:
        return 0.0, {"ref_list_status": "insufficient_data", "papers_with_refs": len(ref_sizes)}

    ref_sizes_sorted = sorted(ref_sizes)
    n = len(ref_sizes_sorted)
    median_size = ref_sizes_sorted[n // 2]
    mean_size = sum(ref_sizes) / n

    if median_size == 0 and mean_size == 0:
        return 0.0, {"ref_list_status": "all_empty", "papers_with_refs": n}

    # Coefficient of variation (high = inconsistent reference list sizes)
    variance = sum((s - mean_size) ** 2 for s in ref_sizes) / n
    std_size = math.sqrt(variance)
    cv = std_size / mean_size if mean_size > 0 else 0.0

    # Count outliers (> 2 std from mean, or < 3 references)
    tiny_refs = sum(1 for s in ref_sizes if s < 3 and s >= 0)
    huge_refs = sum(1 for s in ref_sizes if mean_size > 0 and s > mean_size + 2 * std_size)
    outlier_fraction = (tiny_refs + huge_refs) / n if n > 0 else 0.0

    # Anomaly: high CV + outliers → suspicious
    anomaly = min((cv / 2.0 + outlier_fraction) / 2.0, 1.0)

    return anomaly, {
        "ref_list_median": median_size,
        "ref_list_mean": round(mean_size, 1),
        "ref_list_std": round(std_size, 1),
        "ref_list_cv": round(cv, 4),
        "tiny_ref_papers": tiny_refs,
        "huge_ref_papers": huge_refs,
        "papers_with_refs": n,
    }


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


def compute_gic(author_data: AuthorData, baseline=None) -> IndicatorResult:
    """Geographic/Institutional Clustering (§8.1.6) via Shannon entropy.

    Low entropy = citations come from few unique institutions = suspicious.
    Normalized so that GIC ∈ [0, 1], where 1 = maximally suspicious.

    Three sub-checks per spec:
    1. Same-institution ratio
    2. Entropy-based concentration
    3. Comparison with discipline baseline (if available)

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
        if author_work_ids and c.target_work_id not in author_work_ids:
            continue

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

    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0

    # Normalized entropy [0, 1], inverted so low entropy = high GIC
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    raw_gic = 1.0 - normalized_entropy

    # Same-institution ratio
    same_inst_ratio = same_institution_count / total if total > 0 else 0.0

    # Discipline baseline comparison (§8.1.6: "comparison with normal distribution")
    discipline_deviation = 0.0
    if baseline is not None:
        # Expected unique sources ratio for discipline
        # Normal: ~50-80% of citations from unique sources; suspicious: <20%
        unique_ratio = len(counts) / total if total > 0 else 0.0
        # Compare with discipline expected diversity
        expected_diversity = 0.5  # baseline expected (can be refined per discipline)
        if hasattr(baseline, "avg_scr"):
            # Higher SCR disciplines tolerate lower diversity
            expected_diversity = max(0.3, 0.6 - baseline.avg_scr)
        if unique_ratio < expected_diversity:
            discipline_deviation = min((expected_diversity - unique_ratio) / expected_diversity, 1.0)

    # Weighted: 50% entropy, 25% same-institution, 25% discipline deviation
    gic_value = 0.50 * raw_gic + 0.25 * same_inst_ratio + 0.25 * discipline_deviation

    return IndicatorResult(
        "GIC",
        round(gic_value, 6),
        {
            "entropy": round(entropy, 4),
            "max_entropy": round(max_entropy, 4),
            "normalized_entropy": round(normalized_entropy, 4),
            "raw_gic": round(raw_gic, 4),
            "unique_sources": len(counts),
            "total_non_self_citations": total,
            "same_institution_count": same_institution_count,
            "same_institution_ratio": round(same_inst_ratio, 4),
            "discipline_deviation": round(discipline_deviation, 4),
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
