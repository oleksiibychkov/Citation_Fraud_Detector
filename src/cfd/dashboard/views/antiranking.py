"""Anti-ranking — authors sorted by suspicion score."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t
from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}


def render():
    """Render the anti-ranking page."""
    st.header(t("dashboard.antiranking_header"))
    st.caption(t("dashboard.antiranking_caption"))

    entries = _load_ranking()

    if not entries:
        st.info(t("dashboard.no_analysis_results"))
        return

    # Sorting
    sort_keys = ["fraud_score", "h_index", "citation_count", "publication_count"]
    sort_display = {k: t(f"sort_labels.{k}") for k in sort_keys}
    sort_options = list(sort_display.values())
    sort_label = st.selectbox(t("dashboard.sort_by"), sort_options)
    display_to_key = {v: k for k, v in sort_display.items()}
    sort_col = display_to_key.get(sort_label, "fraud_score")
    ascending = st.checkbox(t("dashboard.ascending"), value=False)

    entries.sort(key=lambda e: e.get(sort_col, 0) or 0, reverse=not ascending)

    # Export
    if st.button(t("dashboard.export_csv_btn")):
        _export_csv(entries)

    # Table
    st.markdown("---")
    header_cols = st.columns([1, 3, 2, 2, 2, 2, 2])
    header_cols[0].write(f"**{t('dashboard.col_rank')}**")
    header_cols[1].write(f"**{t('dashboard.col_author')}**")
    header_cols[2].write(f"**{t('dashboard.col_score')}**")
    header_cols[3].write(f"**{t('dashboard.col_level')}**")
    header_cols[4].write(f"**{t('dashboard.col_h_index')}**")
    header_cols[5].write(f"**{t('dashboard.col_citations')}**")
    header_cols[6].write(f"**{t('dashboard.col_publications')}**")

    for i, entry in enumerate(entries, 1):
        level = entry.get("confidence_level", "normal") or "normal"
        if level not in VALID_LEVELS:
            level = "normal"
        color = LEVEL_COLORS.get(level, "#999999")
        score = entry.get("fraud_score", 0) or 0
        level_label = t(f"level_labels.{level}")

        cols = st.columns([1, 3, 2, 2, 2, 2, 2])
        cols[0].write(str(i))
        cols[1].write(entry.get("author_name", t("dashboard.unknown_author")))
        cols[2].markdown(
            f"<span style='color:{color};font-weight:bold'>{score:.4f}</span>",
            unsafe_allow_html=True,
        )
        cols[3].markdown(f"<span style='color:{color}'>{level_label}</span>", unsafe_allow_html=True)
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
                "author_name": (author or {}).get("full_name") or (author or {}).get("surname", t("dashboard.unknown_author")),
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
    writer.writerow([
        t("dashboard.col_rank"),
        t("dashboard.col_author"),
        t("dashboard.activity_score"),
        t("dashboard.col_level"),
        t("dashboard.col_h_index"),
        t("dashboard.col_citations"),
        t("dashboard.col_publications"),
    ])

    for i, e in enumerate(entries, 1):
        level_label = t(f"level_labels.{e.get('confidence_level', 'normal')}")
        writer.writerow([
            i,
            e.get("author_name", ""),
            e.get("fraud_score", ""),
            level_label,
            e.get("h_index", ""),
            e.get("citation_count", ""),
            e.get("publication_count", ""),
        ])

    csv_filename = "anti-ranking.csv" if t("dashboard.language") == "Language" else "antiranking.csv"
    st.download_button(t("dashboard.download_csv"), buf.getvalue(), csv_filename, "text/csv")
