"""Build mutual citation graph G_mutual for clique/community analysis."""

from __future__ import annotations

from collections import Counter

import networkx as nx

from cfd.data.models import AuthorData, Citation


def _build_work_to_authors(author_data: AuthorData) -> dict[str, set[str]]:
    """Map work_id -> set of author IDs from co_authors data."""
    mapping: dict[str, set[str]] = {}
    for pub in author_data.publications:
        authors = set()
        for ca in pub.co_authors:
            aid = ca.get("author_id", "")
            if aid:
                authors.add(aid)
        if authors:
            mapping[pub.work_id] = authors
    return mapping


def _derive_author_edges(
    citations: list[Citation],
    work_to_authors: dict[str, set[str]],
    our_author_id: str | None = None,
) -> tuple[Counter[tuple[str, str]], Counter[str]]:
    """Derive directed author-to-author citation counts from work-level citations.

    For each citation (source_work -> target_work), every author of source_work
    is considered to cite every author of target_work (excluding self-links).
    """
    pair_counts: Counter[tuple[str, str]] = Counter()
    author_total: Counter[str] = Counter()

    for c in citations:
        src_authors = work_to_authors.get(c.source_work_id, set())
        tgt_authors = work_to_authors.get(c.target_work_id, set())

        for sa in src_authors:
            for ta in tgt_authors:
                if sa != ta:
                    pair_counts[(sa, ta)] += 1
                    author_total[sa] += 1

    return pair_counts, author_total


def build_mutual_graph(
    citations: list[Citation],
    mcr_threshold: float = 0.3,
    author_data: AuthorData | None = None,
) -> nx.Graph:
    """Build undirected mutual citation graph.

    An edge (a, b) exists if the pairwise MCR(a, b) > mcr_threshold.
    MCR(a,b) = 2 * min(cit(a->b), cit(b->a)) / (|cit_from_a| + |cit_from_b|)

    Works with both author-level IDs (legacy) and work-level IDs (via author_data).
    """
    pair_counts: Counter[tuple[str, str]] = Counter()
    author_total: Counter[str] = Counter()

    # Try work-level derivation first (OpenAlex path)
    if author_data is not None:
        work_to_authors = _build_work_to_authors(author_data)
        if work_to_authors:
            pair_counts, author_total = _derive_author_edges(
                citations, work_to_authors, author_data.profile.openalex_id,
            )

    # Fallback: legacy author-level IDs (Scopus path)
    if not pair_counts:
        for c in citations:
            src = c.source_author_id
            tgt = c.target_author_id
            if src is not None and tgt is not None and src != tgt:
                pair_counts[(src, tgt)] += 1
                author_total[src] += 1

    g = nx.Graph()

    seen: set = set()
    for (a, b), a_to_b in pair_counts.items():
        pair_key = (min(a, b), max(a, b))
        if pair_key in seen:
            continue
        seen.add(pair_key)

        b_to_a = pair_counts.get((b, a), 0)
        if b_to_a == 0:
            continue

        total_a = author_total[a]
        total_b = author_total[b]
        denom = total_a + total_b
        if denom == 0:
            continue

        mutual = min(a_to_b, b_to_a)
        mcr = (2 * mutual) / denom

        if mcr > mcr_threshold:
            g.add_edge(a, b, weight=mcr, mcr=mcr)

    return g
