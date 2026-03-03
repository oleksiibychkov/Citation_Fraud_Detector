"""Shared ethical disclaimer for dashboard pages."""

from __future__ import annotations

import streamlit as st

_DISCLAIMER = (
    "Це алгоритмічна оцінка підозрілості, а не остаточний вирок. "
    "Цитатні патерни можуть мати легітимні пояснення (вузька спеціалізація, "
    "оглядові статті, актуальні теми). Результати мають інтерпретуватися "
    "кваліфікованими експертами та перевірятися за кількома джерелами даних."
)


def render_disclaimer():
    """Render the ethical disclaimer at the bottom of a dashboard page."""
    st.markdown("---")
    st.caption(_DISCLAIMER)
