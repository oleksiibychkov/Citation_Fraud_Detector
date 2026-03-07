"""CFD Streamlit Dashboard — entry point."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import set_language, t

st.set_page_config(
    page_title="Citation Fraud Detector",
    page_icon="\U0001f50d",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Active pages (others commented out for now)
_PAGE_KEYS = [
    "dossier",
    "settings",
    # "overview",
    # "compare",
    # "antiranking",
]

# Map page key -> translation key in locale
_PAGE_I18N = {
    "dossier": "dashboard.dossier",
    "settings": "dashboard.settings",
    # "overview": "dashboard.overview",
    # "compare": "dashboard.compare",
    # "antiranking": "dashboard.antiranking",
}

# Map page key -> module to import
_PAGE_MODULES = {
    "dossier": "cfd.dashboard.views.dossier",
    "settings": "cfd.dashboard.views.settings",
    # "overview": "cfd.dashboard.views.overview",
    # "compare": "cfd.dashboard.views.compare",
    # "antiranking": "cfd.dashboard.views.antiranking",
}


def _get_lang() -> str:
    """Return current language from session state."""
    return st.session_state.get("lang", "ua")


def main():
    """Main dashboard entry point."""
    # Language selector at the top of sidebar
    lang_options = {"Українська": "ua", "English": "en"}
    lang_label = st.sidebar.selectbox(
        "Language / Мова",
        list(lang_options.keys()),
        index=0 if _get_lang() == "ua" else 1,
        key="lang_selector",
    )
    lang = lang_options[lang_label]
    if st.session_state.get("lang") != lang:
        st.session_state["lang"] = lang
        set_language(lang)
        st.rerun()
    set_language(lang)

    st.sidebar.title(t("dashboard.app_title"))

    # Use format_func so the radio stores the stable key, not the translated label
    selected_key = st.sidebar.radio(
        t("dashboard.nav_label"),
        _PAGE_KEYS,
        format_func=lambda k: t(_PAGE_I18N[k]),
        key="nav_page",
    )

    # Route to the selected page
    import importlib

    module = importlib.import_module(_PAGE_MODULES[selected_key])
    module.render()


if __name__ == "__main__":
    main()
else:
    main()
