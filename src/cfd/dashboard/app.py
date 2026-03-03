"""CFD Streamlit Dashboard — entry point."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Аналіз публікаційної активності",
    page_icon="\U0001f50d",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main dashboard entry point."""
    st.sidebar.title("Аналіз публікаційної активності")

    page = st.sidebar.radio(
        "Навігація",
        [
            "Огляд спостережень",
            "Досьє автора",
            "Порівняння знімків",
            "Антирейтинг",
            "Налаштування",
        ],
    )

    if page == "Огляд спостережень":
        from cfd.dashboard.pages.overview import render

        render()
    elif page == "Досьє автора":
        from cfd.dashboard.pages.dossier import render

        render()
    elif page == "Порівняння знімків":
        from cfd.dashboard.pages.compare import render

        render()
    elif page == "Антирейтинг":
        from cfd.dashboard.pages.antiranking import render

        render()
    elif page == "Налаштування":
        from cfd.dashboard.pages.settings import render

        render()


if __name__ == "__main__":
    main()
else:
    main()
