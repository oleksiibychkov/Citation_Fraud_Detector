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

# Pages available to all authenticated users
_USER_PAGES = ["dossier"]

# Pages available only to admin
_ADMIN_PAGES = [
    "journal_dossier",
    "organization",
    "users",
    "settings",
    # "overview",
    # "compare",
    # "antiranking",
]

# Map page key -> translation key in locale
_PAGE_I18N = {
    "dossier": "dashboard.dossier",
    "journal_dossier": "dashboard.journal_dossier",
    "organization": "dashboard.organization",
    "users": "dashboard.users",
    "settings": "dashboard.settings",
    # "overview": "dashboard.overview",
    # "compare": "dashboard.compare",
    # "antiranking": "dashboard.antiranking",
}

# Map page key -> module to import
_PAGE_MODULES = {
    "dossier": "cfd.dashboard.views.dossier",
    "journal_dossier": "cfd.dashboard.views.journal_dossier",
    "organization": "cfd.dashboard.views.organization",
    "users": "cfd.dashboard.views.users",
    "settings": "cfd.dashboard.views.settings",
    # "overview": "cfd.dashboard.views.overview",
    # "compare": "cfd.dashboard.views.compare",
    # "antiranking": "cfd.dashboard.views.antiranking",
}


def _get_lang() -> str:
    """Return current language from session state."""
    return st.session_state.get("lang", "ua")


def _setup_language():
    """Setup language selector and return current lang."""
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


def main():
    """Main dashboard entry point."""
    _setup_language()

    # --- Authentication gate ---
    from cfd.dashboard.auth import is_admin, logout, require_auth

    user = require_auth()
    if user is None:
        return

    # --- User is authenticated ---
    st.sidebar.title(t("dashboard.app_title"))

    # Show user info & logout
    st.sidebar.markdown(f"**{user.get('surname', '')}**")
    st.sidebar.caption(user.get("orcid", ""))
    if st.sidebar.button(t("auth.logout_btn")):
        logout()
        st.rerun()

    st.sidebar.markdown("---")

    # Build page list based on role
    admin = is_admin(user)
    page_keys = list(_USER_PAGES)
    if admin:
        page_keys.extend(_ADMIN_PAGES)

    # Navigation
    selected_key = st.sidebar.radio(
        t("dashboard.nav_label"),
        page_keys,
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
