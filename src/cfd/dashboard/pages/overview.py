"""Огляд спостережень — таблиця з кольоровими оцінками та фільтрами."""

from __future__ import annotations

import streamlit as st

from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}

LEVEL_LABELS = {
    "normal": "НОРМА",
    "low": "НИЗЬКИЙ",
    "moderate": "ПОМІРНИЙ",
    "high": "ВИСОКИЙ",
    "critical": "КРИТИЧНИЙ",
}


def render():
    """Render the overview / watchlist page."""
    st.header("Огляд спостережень")

    entries = _load_watchlist()

    if not entries:
        st.info(
            "Список спостережень порожній. "
            "Використайте `cfd watchlist add` для додавання авторів, "
            "або перейдіть до «Досьє автора» для аналізу."
        )
        return

    # Фільтри
    col1, col2 = st.columns(2)
    with col1:
        min_score = st.slider("Мін. оцінка підозрілості", 0.0, 1.0, 0.0, 0.05)
    with col2:
        level_options = list(LEVEL_LABELS.values())
        level_filter_ua = st.multiselect(
            "Рівень ризику",
            level_options,
            default=level_options,
        )
        # Map back to English keys
        ua_to_en = {v: k for k, v in LEVEL_LABELS.items()}
        level_filter = [ua_to_en[la] for la in level_filter_ua if la in ua_to_en]

    filtered = [
        e for e in entries
        if e.get("fraud_score", 0) >= min_score
        and e.get("confidence_level", "normal") in level_filter
    ]

    if not filtered:
        st.warning("Жодний запис не відповідає поточним фільтрам.")
        return

    # Таблиця
    for entry in filtered:
        level = entry.get("confidence_level", "normal") or "normal"
        if level not in VALID_LEVELS:
            level = "normal"
        color = LEVEL_COLORS.get(level, "#999999")
        score = entry.get("fraud_score", 0) or 0
        level_ua = LEVEL_LABELS.get(level, level.upper())

        col_name, col_score, col_level, col_reason = st.columns([3, 1, 1, 3])
        with col_name:
            st.write(f"**{entry.get('author_name', 'Невідомий')}**")
        with col_score:
            st.markdown(f"<span style='color:{color};font-weight:bold'>{score:.4f}</span>", unsafe_allow_html=True)
        with col_level:
            st.markdown(f"<span style='color:{color}'>{level_ua}</span>", unsafe_allow_html=True)
        with col_reason:
            st.write(entry.get("reason", "\u2014"))

    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()


def _load_watchlist() -> list[dict]:
    """Load watchlist entries enriched with author info and latest scores."""
    try:
        from cfd.config.settings import Settings
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.authors import AuthorRepository
        from cfd.db.repositories.fraud_scores import FraudScoreRepository
        from cfd.db.repositories.watchlist import WatchlistRepository

        settings = Settings()
        if not settings.supabase_url or not settings.supabase_key:
            return []

        client = get_supabase_client(settings)
        watchlist_repo = WatchlistRepository(client)
        author_repo = AuthorRepository(client)
        score_repo = FraudScoreRepository(client)

        raw_entries = watchlist_repo.get_active()

        enriched = []
        for entry in raw_entries:
            author_id = entry.get("author_id")
            author = author_repo.get_by_id(author_id) if author_id is not None else None
            latest_score = score_repo.get_latest_by_author(author_id) if author_id is not None else None

            enriched.append({
                "author_name": (author or {}).get("full_name") or (author or {}).get("surname", "Невідомий"),
                "fraud_score": (latest_score or {}).get("score") or 0,
                "confidence_level": (latest_score or {}).get("confidence_level") or "normal",
                "reason": entry.get("reason", "\u2014"),
                "author_id": author_id,
            })
        return enriched
    except Exception:
        return []
