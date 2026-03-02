"""Shared ethical disclaimer for dashboard pages."""

from __future__ import annotations

import streamlit as st

_DISCLAIMER = {
    "ua": "Це оцінка підозрілості, а не вирок. Остаточне рішення приймає людина.",
    "en": "This is a suspicion score, not a verdict. Final decision rests with a human.",
}


def render_disclaimer():
    """Render the ethical disclaimer at the bottom of a dashboard page."""
    lang = st.session_state.get("lang", "ua")
    st.markdown("---")
    st.caption(_DISCLAIMER.get(lang, _DISCLAIMER["en"]))
