"""Shared color palette for visualizations."""

from __future__ import annotations

# Confidence level color mapping (hex)
LEVEL_COLORS: dict[str, str] = {
    "normal": "#2ecc71",
    "low": "#f1c40f",
    "moderate": "#e67e22",
    "high": "#e74c3c",
    "critical": "#c0392b",
}

# Indicator severity gradient (for heatmaps and continuous scales)
SEVERITY_COLORSCALE: list[list] = [
    [0.0, "#ffffff"],
    [0.2, "#d5f5e3"],
    [0.4, "#f9e79f"],
    [0.6, "#f5b041"],
    [0.8, "#e74c3c"],
    [1.0, "#922b21"],
]

# Chart styling defaults
CHART_TEMPLATE = "plotly_white"
FONT_FAMILY = "Arial, sans-serif"
TITLE_FONT_SIZE = 16
AXIS_FONT_SIZE = 12


def get_level_color(level: str) -> str:
    """Get hex color for a confidence level."""
    return LEVEL_COLORS.get(level, "#95a5a6")
