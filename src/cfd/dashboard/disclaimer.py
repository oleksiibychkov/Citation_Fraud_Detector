"""Shared ethical disclaimer for dashboard pages."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t


def render_disclaimer():
    """Render the ethical disclaimer at the bottom of a dashboard page."""
    st.markdown("---")
    st.caption(t("dashboard.disclaimer_text"))
