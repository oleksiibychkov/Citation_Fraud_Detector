"""Порівняння знімків — часові ряди та дельта-діаграми для авторів зі списку спостережень."""

from __future__ import annotations

import streamlit as st


def render():
    """Render the snapshot comparison page."""
    st.header("Порівняння знімків")

    author_id = st.number_input("ID автора в базі даних", min_value=1, step=1)
    num_snapshots = st.slider("Кількість знімків", 2, 20, 5)

    if not st.button("Порівняти"):
        return

    snapshots = _load_snapshots(author_id, num_snapshots)

    if not snapshots:
        st.info("Знімки для цього автора не знайдено.")
        return

    if len(snapshots) < 2:
        st.warning("Доступний лише один знімок — порівняння неможливе.")
        _show_single(snapshots[0])
        from cfd.dashboard.disclaimer import render_disclaimer
        render_disclaimer()
        return

    # Графік часового ряду
    st.subheader("Динаміка оцінки")
    _render_timeline(snapshots)

    # Таблиця змін
    st.subheader("Останній vs попередній")
    latest = snapshots[0]
    previous = snapshots[1]

    metrics = [
        ("fraud_score", "Оцінка шахрайства"),
        ("h_index", "h-індекс"),
        ("citation_count", "Цитувань"),
        ("publication_count", "Публікацій"),
    ]

    cols = st.columns(len(metrics))
    for i, (key, label) in enumerate(metrics):
        prev_val = previous.get(key, previous.get("metrics", {}).get(key))
        curr_val = latest.get(key, latest.get("metrics", {}).get(key))

        if prev_val is not None and curr_val is not None:
            try:
                delta = float(curr_val) - float(prev_val)
                cols[i].metric(label, f"{curr_val}", f"{delta:+.4f}")
            except (TypeError, ValueError):
                cols[i].metric(label, str(curr_val))
        else:
            cols[i].metric(label, str(curr_val or "\u2014"))

    # Попередження про зміну версії алгоритму
    prev_algo = previous.get("algorithm_version", "?")
    curr_algo = latest.get("algorithm_version", "?")
    if prev_algo != curr_algo:
        st.warning(f"Версія алгоритму змінилась: {prev_algo} \u2192 {curr_algo}")

    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()


def _load_snapshots(author_id: int, limit: int) -> list[dict]:
    """Load snapshots from database."""
    try:
        from cfd.config.settings import Settings
        from cfd.db.client import get_supabase_client
        from cfd.db.repositories.snapshots import SnapshotRepository

        settings = Settings()
        client = get_supabase_client(settings)
        repo = SnapshotRepository(client)
        return repo.get_by_author_id(author_id, limit=limit)
    except Exception:
        st.error("Не вдалося підключитися до бази даних.")
        return []


def _show_single(snapshot: dict):
    """Display a single snapshot."""
    labels = {
        "fraud_score": "Оцінка шахрайства",
        "h_index": "h-індекс",
        "citation_count": "Цитувань",
        "publication_count": "Публікацій",
    }
    for key, label in labels.items():
        val = snapshot.get(key, snapshot.get("metrics", {}).get(key, "\u2014"))
        st.write(f"**{label}**: {val}")


def _render_timeline(snapshots: list[dict]):
    """Render a score timeline chart."""
    try:
        import plotly.graph_objects as go

        dates = [(s.get("snapshot_date") or s.get("created_at") or "")[:10] for s in reversed(snapshots)]
        scores = [s.get("fraud_score", 0) for s in reversed(snapshots)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers", name="Оцінка шахрайства"))
        fig.update_layout(
            title="Динаміка оцінки шахрайства",
            xaxis_title="Дата",
            yaxis_title="Оцінка",
            yaxis={"range": [0, 1]},
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("Для графіка потрібен Plotly.")
