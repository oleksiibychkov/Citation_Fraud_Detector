"""Build mutual citation graph G_mutual for clique/community analysis."""

from __future__ import annotations

from collections import Counter

import networkx as nx

from cfd.data.models import Citation


def build_mutual_graph(citations: list[Citation], mcr_threshold: float = 0.3) -> nx.Graph:
    """Build undirected mutual citation graph.

    An edge (a, b) exists if the pairwise MCR(a, b) > mcr_threshold.
    MCR(a,b) = 2 * min(cit(a->b), cit(b->a)) / (|cit_from_a| + |cit_from_b|)
    """
    # Count directed citations between author pairs
    pair_counts: Counter[tuple[int, int]] = Counter()
    author_total: Counter[int] = Counter()

    for c in citations:
        src = c.source_author_id
        tgt = c.target_author_id
        if src is not None and tgt is not None and src != tgt:
            pair_counts[(src, tgt)] += 1
            author_total[src] += 1

    g = nx.Graph()

    # Check each pair for mutual citation threshold
    seen: set[tuple[int, int]] = set()
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
