"""Graph construction from citation data."""

from __future__ import annotations

import networkx as nx

from cfd.data.models import AuthorData, Citation


def build_citation_graph(author_data: AuthorData) -> nx.DiGraph:
    """Build directed citation graph G=(V,E) from collected data.

    Nodes represent works (publications). Edges represent citations.
    """
    g = nx.DiGraph()

    # Add nodes for all publications
    for pub in author_data.publications:
        g.add_node(
            pub.work_id,
            type="publication",
            title=pub.title,
            date=str(pub.publication_date) if pub.publication_date else None,
            citation_count=pub.citation_count,
            journal=pub.journal,
        )

    # Add edges for citations
    for cit in author_data.citations:
        # Ensure both nodes exist (add external nodes as needed)
        if cit.source_work_id not in g:
            g.add_node(cit.source_work_id, type="external")
        if cit.target_work_id not in g:
            g.add_node(cit.target_work_id, type="external")

        g.add_edge(
            cit.source_work_id,
            cit.target_work_id,
            citation_date=str(cit.citation_date) if cit.citation_date else None,
            is_self_citation=cit.is_self_citation,
        )

    return g


def build_author_graph(citations: list[Citation]) -> nx.DiGraph:
    """Build aggregated author graph G_auth = (A, E_auth).

    Nodes are author IDs. Edge (a, b) exists if any publication by a
    cites any publication by b. Edge weight = number of such citations.
    """
    g = nx.DiGraph()
    edge_counts: dict[tuple[int, int], int] = {}

    for cit in citations:
        if cit.source_author_id and cit.target_author_id and cit.source_author_id != cit.target_author_id:
            key = (cit.source_author_id, cit.target_author_id)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    for (src, tgt), weight in edge_counts.items():
        g.add_edge(src, tgt, weight=weight)

    return g
