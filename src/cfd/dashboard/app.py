"""CFD Streamlit Dashboard — entry point."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Citation Fraud Detector",
    page_icon="\U0001f50d",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main dashboard entry point."""
    # Sidebar — navigation & language toggle
    st.sidebar.title("Citation Fraud Detector")

    lang = st.sidebar.selectbox("Language / Мова", ["ua", "en"], index=0)
    st.session_state["lang"] = lang

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Author Dossier", "Snapshot Compare", "Anti-Ranking"],
    )

    # Route to page
    if page == "Overview":
        from cfd.dashboard.pages.overview import render

        render()
    elif page == "Author Dossier":
        from cfd.dashboard.pages.dossier import render

        render()
    elif page == "Snapshot Compare":
        from cfd.dashboard.pages.compare import render

        render()
    elif page == "Anti-Ranking":
        from cfd.dashboard.pages.antiranking import render

        render()


if __name__ == "__main__":
    main()
else:
    # When launched via `streamlit run app.py`
    main()
