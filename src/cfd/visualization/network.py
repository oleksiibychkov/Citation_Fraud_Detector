"""Citation network graph visualization."""

from __future__ import annotations

import logging

import networkx as nx
import plotly.graph_objects as go

from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorData
from cfd.graph.builder import build_citation_graph
from cfd.visualization.colors import CHART_TEMPLATE, FONT_FAMILY, TITLE_FONT_SIZE, get_level_color

logger = logging.getLogger(__name__)


def build_network_figure(
    author_data: AuthorData,
    result: AnalysisResult,
    layout_seed: int = 42,
    max_nodes: int = 500,
) -> go.Figure:
    """Build interactive citation network graph.

    Node color = confidence level, size = citation count.
    Self-citation edges drawn with distinct dash style.
    """
    graph = build_citation_graph(author_data)

    if len(graph.nodes) == 0:
        fig = go.Figure()
        fig.update_layout(
            title="Citation Network (no data)",
            template=CHART_TEMPLATE,
            font={"family": FONT_FAMILY},
        )
        return fig

    # Subsample if too many nodes
    if len(graph.nodes) > max_nodes:
        graph = _subsample_graph(graph, author_data, max_nodes)

    # Compute layout
    pos = nx.spring_layout(graph, seed=layout_seed, k=1.5 / (len(graph.nodes) ** 0.5 + 1))

    # Build edge traces
    edge_x, edge_y = [], []
    self_edge_x, self_edge_y = [], []

    self_cit_pairs = set()
    for c in author_data.citations:
        if c.is_self_citation:
            self_cit_pairs.add((c.source_work_id, c.target_work_id))

    for u, v in graph.edges():
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            if (u, v) in self_cit_pairs:
                self_edge_x.extend([x0, x1, None])
                self_edge_y.extend([y0, y1, None])
            else:
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

    traces = []

    # External citation edges
    if edge_x:
        traces.append(go.Scatter(
            x=edge_x, y=edge_y,
            mode="lines",
            line={"width": 0.5, "color": "#cccccc"},
            hoverinfo="none",
            name="Citations",
        ))

    # Self-citation edges (dashed)
    if self_edge_x:
        traces.append(go.Scatter(
            x=self_edge_x, y=self_edge_y,
            mode="lines",
            line={"width": 1.0, "color": "#e74c3c", "dash": "dash"},
            hoverinfo="none",
            name="Self-citations",
        ))

    # Node trace
    node_x, node_y, node_sizes, node_colors, node_text = [], [], [], [], []
    level_color = get_level_color(result.confidence_level)

    # Build publication citation count map
    pub_citations = {p.work_id: p.citation_count for p in author_data.publications}

    for node in graph.nodes():
        if node not in pos:
            continue
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        cit_count = pub_citations.get(node, 1)
        node_sizes.append(max(5, min(30, cit_count ** 0.5 * 3)))

        # Author's own publications get the level color, others are grey
        if node in pub_citations:
            node_colors.append(level_color)
        else:
            node_colors.append("#95a5a6")

        node_text.append(f"{node}<br>Citations: {cit_count}")

    traces.append(go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        marker={
            "size": node_sizes,
            "color": node_colors,
            "line": {"width": 1, "color": "#333333"},
        },
        text=node_text,
        hoverinfo="text",
        name="Publications",
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"Citation Network — {result.author_profile.full_name or result.author_profile.surname}",
        template=CHART_TEMPLATE,
        font={"family": FONT_FAMILY, "size": TITLE_FONT_SIZE},
        showlegend=True,
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        hovermode="closest",
    )

    return fig


def _subsample_graph(graph: nx.DiGraph, author_data: AuthorData, max_nodes: int) -> nx.DiGraph:
    """Subsample graph keeping the most important nodes."""
    # Keep all author's publications
    author_nodes = {p.work_id for p in author_data.publications}

    # Rank remaining nodes by degree
    other_nodes = [(n, graph.degree(n)) for n in graph.nodes() if n not in author_nodes]
    other_nodes.sort(key=lambda x: x[1], reverse=True)

    remaining = max_nodes - len(author_nodes)
    keep_nodes = author_nodes | {n for n, _ in other_nodes[:max(0, remaining)]}

    return graph.subgraph(keep_nodes).copy()
