"""Anti-Ranking page — sortable table of authors ranked by fraud score."""

from __future__ import annotations

import streamlit as st

from cfd.visualization.colors import LEVEL_COLORS


def render():
    """Render the anti-ranking page."""
    st.header("Anti-Ranking")
    st.caption("Authors ranked by fraud score (highest suspicion first)")

    entries = _load_ranking()

    if not entries:
        st.info("No analysis results available. Run `cfd analyze` or `cfd batch` first.")
        return

    # Sort control
    sort_col = st.selectbox("Sort by", ["fraud_score", "h_index", "citation_count", "publication_count"])
    ascending = st.checkbox("Ascending", value=False)

    entries.sort(key=lambda e: e.get(sort_col, 0) or 0, reverse=not ascending)

    # Export button
    if st.button("Export CSV"):
        _export_csv(entries)

    # Render table
    st.markdown("---")
    header_cols = st.columns([1, 3, 2, 2, 2, 2, 2])
    header_cols[0].write("**#**")
    header_cols[1].write("**Author**")
    header_cols[2].write("**Fraud Score**")
    header_cols[3].write("**Level**")
    header_cols[4].write("**h-index**")
    header_cols[5].write("**Citations**")
    header_cols[6].write("**Publications**")

    for i, entry in enumerate(entries, 1):
        level = entry.get("confidence_level", "normal")
        color = LEVEL_COLORS.get(level, "#999999")
        score = entry.get("fraud_score", 0)

        cols = st.columns([1, 3, 2, 2, 2, 2, 2])
        cols[0].write(str(i))
        cols[1].write(entry.get("author_name", "Unknown"))
        cols[2].markdown(
            f"<span style='color:{color};font-weight:bold'>{score:.4f}</span>",
            unsafe_allow_html=True,
        )
        cols[3].markdown(f"<span style='color:{color}'>{level.upper()}</span>", unsafe_allow_html=True)
        cols[4].write(str(entry.get("h_index", "—")))
        cols[5].write(str(entry.get("citation_count", "—")))
        cols[6].write(str(entry.get("publication_count", "—")))

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

        # Enrich with author info
        enriched = []
        for row in scores:
            author_id = row.get("author_id")
            author = author_repo.get_by_id(author_id) if author_id else None
            enriched.append({
                "fraud_score": row.get("score", 0),
                "confidence_level": row.get("confidence_level", "normal"),
                "author_name": (author or {}).get("full_name") or (author or {}).get("surname", "Unknown"),
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
    writer.writerow(["rank", "author_name", "fraud_score", "confidence_level", "h_index", "citations", "publications"])

    for i, e in enumerate(entries, 1):
        writer.writerow([
            i,
            e.get("author_name", ""),
            e.get("fraud_score", ""),
            e.get("confidence_level", ""),
            e.get("h_index", ""),
            e.get("citation_count", ""),
            e.get("publication_count", ""),
        ])

    st.download_button("Download CSV", buf.getvalue(), "antiranking.csv", "text/csv")
