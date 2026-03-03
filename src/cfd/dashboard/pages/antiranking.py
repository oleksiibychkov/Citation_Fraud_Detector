"""Антирейтинг — таблиця авторів, відсортована за оцінкою шахрайства."""

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

SORT_LABELS = {
    "fraud_score": "Оцінка шахрайства",
    "h_index": "h-індекс",
    "citation_count": "Цитувань",
    "publication_count": "Публікацій",
}


def render():
    """Render the anti-ranking page."""
    st.header("Антирейтинг")
    st.caption("Автори, відсортовані за оцінкою підозрілості (найвища першою)")

    entries = _load_ranking()

    if not entries:
        st.info(
            "Результати аналізу відсутні. "
            "Спочатку виконайте аналіз через «Досьє автора» або `cfd analyze`."
        )
        return

    # Сортування
    sort_labels = list(SORT_LABELS.values())
    sort_label = st.selectbox("Сортувати за", sort_labels)
    label_to_key = {v: k for k, v in SORT_LABELS.items()}
    sort_col = label_to_key.get(sort_label, "fraud_score")
    ascending = st.checkbox("За зростанням", value=False)

    entries.sort(key=lambda e: e.get(sort_col, 0) or 0, reverse=not ascending)

    # Експорт
    if st.button("Експорт CSV"):
        _export_csv(entries)

    # Таблиця
    st.markdown("---")
    header_cols = st.columns([1, 3, 2, 2, 2, 2, 2])
    header_cols[0].write("**#**")
    header_cols[1].write("**Автор**")
    header_cols[2].write("**Оцінка**")
    header_cols[3].write("**Рівень**")
    header_cols[4].write("**h-індекс**")
    header_cols[5].write("**Цитувань**")
    header_cols[6].write("**Публікацій**")

    for i, entry in enumerate(entries, 1):
        level = entry.get("confidence_level", "normal") or "normal"
        if level not in VALID_LEVELS:
            level = "normal"
        color = LEVEL_COLORS.get(level, "#999999")
        score = entry.get("fraud_score", 0) or 0
        level_ua = LEVEL_LABELS.get(level, level.upper())

        cols = st.columns([1, 3, 2, 2, 2, 2, 2])
        cols[0].write(str(i))
        cols[1].write(entry.get("author_name", "Невідомий"))
        cols[2].markdown(
            f"<span style='color:{color};font-weight:bold'>{score:.4f}</span>",
            unsafe_allow_html=True,
        )
        cols[3].markdown(f"<span style='color:{color}'>{level_ua}</span>", unsafe_allow_html=True)
        cols[4].write(str(entry.get("h_index", "\u2014")))
        cols[5].write(str(entry.get("citation_count", "\u2014")))
        cols[6].write(str(entry.get("publication_count", "\u2014")))

    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()


def _load_ranking() -> list[dict]:
    """Load ranking data from database, joined with author info."""
    try:
        from cfd.config.settings import Settings
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.authors import AuthorRepository
        from cfd.db.repositories.fraud_scores import FraudScoreRepository

        settings = Settings()
        if not settings.supabase_url or not settings.supabase_key:
            return []

        client = get_supabase_client(settings)
        score_repo = FraudScoreRepository(client)
        author_repo = AuthorRepository(client)

        scores = score_repo.get_all_ranked()

        enriched = []
        for row in scores:
            author_id = row.get("author_id")
            author = author_repo.get_by_id(author_id) if author_id is not None else None
            enriched.append({
                "fraud_score": row.get("score") or 0,
                "confidence_level": row.get("confidence_level") or "normal",
                "author_name": (author or {}).get("full_name") or (author or {}).get("surname", "Невідомий"),
                "h_index": (author or {}).get("h_index"),
                "citation_count": (author or {}).get("citation_count"),
                "publication_count": (author or {}).get("publication_count"),
                "author_id": author_id,
            })
        return enriched
    except Exception:
        return []


def _export_csv(entries: list[dict]):
    """Generate a CSV download button."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Автор", "Оцінка шахрайства", "Рівень ризику", "h-індекс", "Цитувань", "Публікацій"])

    for i, e in enumerate(entries, 1):
        level_ua = LEVEL_LABELS.get(e.get("confidence_level", "normal"), "")
        writer.writerow([
            i,
            e.get("author_name", ""),
            e.get("fraud_score", ""),
            level_ua,
            e.get("h_index", ""),
            e.get("citation_count", ""),
            e.get("publication_count", ""),
        ])

    st.download_button("Завантажити CSV", buf.getvalue(), "антирейтинг.csv", "text/csv")
