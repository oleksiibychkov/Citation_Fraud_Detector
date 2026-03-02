"""Temporal visualization: h(t) vs N(t), spike charts, baseline overlay."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cfd.analysis.baselines import DisciplineBaseline
from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorData
from cfd.graph.metrics import _extract_counts_by_year
from cfd.visualization.colors import CHART_TEMPLATE, FONT_FAMILY, LEVEL_COLORS

logger = logging.getLogger(__name__)


def build_ht_nt_figure(author_data: AuthorData) -> go.Figure:
    """Build dual-axis line chart: cumulative citations h(t) vs cumulative publications N(t)."""
    # Build yearly publication counts
    pub_yearly: Counter = Counter()
    for pub in author_data.publications:
        if pub.publication_date:
            pub_yearly[pub.publication_date.year] += 1

    # Build yearly citation counts
    cit_yearly = _extract_counts_by_year(author_data)
    if not cit_yearly:
        cit_yearly = Counter()
        for c in author_data.citations:
            if c.citation_date:
                cit_yearly[c.citation_date.year] += 1

    if not pub_yearly and not cit_yearly:
        fig = go.Figure()
        fig.update_layout(title="h(t) vs N(t) — No temporal data", template=CHART_TEMPLATE)
        return fig

    all_years = sorted(set(pub_yearly.keys()) | set(cit_yearly.keys()))

    # Cumulative values
    cum_pubs = np.cumsum([pub_yearly.get(y, 0) for y in all_years])
    cum_cits = np.cumsum([cit_yearly.get(y, 0) for y in all_years])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=all_years, y=cum_cits.tolist(),
            name="Cumulative Citations h(t)",
            line={"color": "#3498db", "width": 2},
            mode="lines+markers",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=all_years, y=cum_pubs.tolist(),
            name="Cumulative Publications N(t)",
            line={"color": "#2ecc71", "width": 2, "dash": "dash"},
            mode="lines+markers",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="h(t) vs N(t) — Citation and Publication Growth",
        template=CHART_TEMPLATE,
        font={"family": FONT_FAMILY},
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text="Cumulative Citations", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Publications", secondary_y=True)

    return fig


def build_spike_chart(
    author_data: AuthorData,
    result: AnalysisResult,
    z_threshold: float = 3.0,
) -> go.Figure:
    """Build yearly citation bar chart with anomaly years highlighted."""
    # Extract TA indicator details
    ta_details = {}
    for ind in result.indicators:
        if ind.indicator_type == "TA":
            ta_details = ind.details
            break

    yearly_counts = ta_details.get("yearly_counts", {})
    spike_year = ta_details.get("spike_year")

    if not yearly_counts:
        # Fallback: build from citations
        cit_yearly = _extract_counts_by_year(author_data)
        if not cit_yearly:
            for c in author_data.citations:
                if c.citation_date:
                    cit_yearly[c.citation_date.year] += 1
        yearly_counts = {str(y): int(v) for y, v in cit_yearly.items()}

    if not yearly_counts:
        fig = go.Figure()
        fig.update_layout(title="Citation Timeline — No temporal data", template=CHART_TEMPLATE)
        return fig

    years = sorted(yearly_counts.keys(), key=lambda y: int(y))
    values = [yearly_counts[y] for y in years]

    # Compute z-scores for coloring
    arr = np.array(values, dtype=float)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr))

    colors = []
    for i, y in enumerate(years):
        z = (values[i] - mean_val) / std_val if std_val > 0 else 0.0
        if str(y) == str(spike_year) or z > z_threshold:
            colors.append(LEVEL_COLORS["critical"])
        elif z > z_threshold * 0.5:
            colors.append(LEVEL_COLORS["moderate"])
        else:
            colors.append(LEVEL_COLORS["normal"])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=years, y=values,
        marker_color=colors,
        name="Citations per Year",
        text=values,
        textposition="auto",
    ))

    # Add mean line
    fig.add_hline(
        y=mean_val,
        line_dash="dash",
        line_color="#7f8c8d",
        annotation_text=f"Mean: {mean_val:.1f}",
    )

    # Add threshold line
    if std_val > 0:
        threshold_val = mean_val + z_threshold * std_val
        fig.add_hline(
            y=threshold_val,
            line_dash="dot",
            line_color="#e74c3c",
            annotation_text=f"Z={z_threshold} threshold",
        )

    fig.update_layout(
        title="Citation Timeline with Anomaly Detection",
        template=CHART_TEMPLATE,
        font={"family": FONT_FAMILY},
        xaxis_title="Year",
        yaxis_title="Citation Count",
    )

    return fig


def build_baseline_overlay(
    author_data: AuthorData,
    baseline: DisciplineBaseline,
) -> go.Figure:
    """Overlay discipline baseline on author's citation accumulation curve."""
    # Build per-paper average citations by age
    paper_ages: dict[int, list[int]] = {}  # age_years → [citation_counts]
    current_year = max(
        (p.publication_date.year for p in author_data.publications if p.publication_date),
        default=datetime.now(UTC).year,
    )

    for pub in author_data.publications:
        if pub.publication_date:
            age = current_year - pub.publication_date.year
            if age >= 0:
                paper_ages.setdefault(age, []).append(pub.citation_count)

    if not paper_ages:
        fig = go.Figure()
        fig.update_layout(title="Baseline Overlay — No data", template=CHART_TEMPLATE)
        return fig

    ages = sorted(paper_ages.keys())
    avg_cits = [np.mean(paper_ages[a]) for a in ages]

    # Expected citations based on discipline baseline (exponential decay model)
    import math

    half_life = baseline.citation_half_life_years
    expected = []
    for a in ages:
        if a == 0:
            expected.append(0.0)
        else:
            decay = 1.0 - math.pow(2.0, -a / half_life)
            norm = 1.0 - math.pow(2.0, -1.0 / half_life)
            expected.append(baseline.avg_citations_per_paper * (decay / norm) if norm > 0 else 0.0)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ages, y=avg_cits,
        name="Author (avg per paper)",
        mode="lines+markers",
        line={"color": "#3498db", "width": 2},
    ))

    fig.add_trace(go.Scatter(
        x=ages, y=expected,
        name=f"Baseline ({baseline.discipline})",
        mode="lines",
        line={"color": "#e67e22", "width": 2, "dash": "dash"},
        fill="tonexty",
        fillcolor="rgba(230, 126, 34, 0.1)",
    ))

    fig.update_layout(
        title=f"Citation Accumulation vs {baseline.discipline} Baseline",
        template=CHART_TEMPLATE,
        font={"family": FONT_FAMILY},
        xaxis_title="Paper Age (years)",
        yaxis_title="Average Citations per Paper",
    )

    return fig
