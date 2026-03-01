"""Mutual citation heatmap visualization."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

import plotly.graph_objects as go

from cfd.data.models import AuthorData
from cfd.visualization.colors import CHART_TEMPLATE, FONT_FAMILY, SEVERITY_COLORSCALE

logger = logging.getLogger(__name__)


def build_mutual_heatmap(
    author_data: AuthorData,
    mcr_threshold: float = 0.3,
) -> go.Figure:
    """Build mutual citation intensity heatmap.

    Shows citation exchange between author pairs as a matrix.
    Intensity = MCR value between each pair.
    """
    # Count directed citations between author pairs
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)
    author_totals: Counter = Counter()

    for c in author_data.citations:
        if c.source_author_id is not None and c.target_author_id is not None and not c.is_self_citation:
            pair_counts[(c.source_author_id, c.target_author_id)] += 1
            author_totals[c.source_author_id] += 1

    if not pair_counts:
        fig = go.Figure()
        fig.update_layout(title="Mutual Citation Heatmap — No data", template=CHART_TEMPLATE)
        return fig

    # Collect all unique authors
    all_authors = sorted(set(a for pair in pair_counts for a in pair))

    if len(all_authors) < 2:
        fig = go.Figure()
        fig.update_layout(title="Mutual Citation Heatmap — Insufficient authors", template=CHART_TEMPLATE)
        return fig

    # Limit to top N authors by citation activity
    max_authors = 30
    if len(all_authors) > max_authors:
        top_authors = author_totals.most_common(max_authors)
        all_authors = sorted([a for a, _ in top_authors])

    # Build MCR matrix
    n = len(all_authors)
    matrix = [[0.0] * n for _ in range(n)]

    for i, a in enumerate(all_authors):
        for j, b in enumerate(all_authors):
            if i == j:
                continue
            a_cites_b = pair_counts.get((a, b), 0)
            b_cites_a = pair_counts.get((b, a), 0)
            mutual = min(a_cites_b, b_cites_a)
            total = author_totals.get(a, 0) + author_totals.get(b, 0)
            if total > 0:
                mcr = (2 * mutual) / total
                matrix[i][j] = round(mcr, 4)

    labels = [str(a) for a in all_authors]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=labels,
        y=labels,
        colorscale=SEVERITY_COLORSCALE,
        zmin=0.0,
        zmax=1.0,
        colorbar={"title": "MCR"},
        hovertemplate="Author %{x} ↔ %{y}<br>MCR: %{z:.4f}<extra></extra>",
    ))

    fig.update_layout(
        title="Mutual Citation Ratio Heatmap",
        template=CHART_TEMPLATE,
        font={"family": FONT_FAMILY},
        xaxis_title="Author ID",
        yaxis_title="Author ID",
        xaxis={"tickangle": 45},
    )

    return fig
