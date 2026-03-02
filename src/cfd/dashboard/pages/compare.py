"""Snapshot Compare page — timeline and delta charts for watchlisted authors."""

from __future__ import annotations

import streamlit as st


def render():
    """Render the snapshot comparison page."""
    st.header("Snapshot Comparison")

    author_id = st.number_input("Author database ID", min_value=1, step=1)
    num_snapshots = st.slider("Number of snapshots", 2, 20, 5)

    if not st.button("Compare"):
        return

    snapshots = _load_snapshots(author_id, num_snapshots)

    if not snapshots:
        st.info("No snapshots found for this author.")
        return

    if len(snapshots) < 2:
        st.warning("Only one snapshot available — no comparison possible.")
        _show_single(snapshots[0])
        from cfd.dashboard.disclaimer import render_disclaimer
        render_disclaimer()
        return

    # Timeline chart
    st.subheader("Score Timeline")
    _render_timeline(snapshots)

    # Delta table
    st.subheader("Latest vs Previous")
    latest = snapshots[0]
    previous = snapshots[1]

    metrics = [
        ("fraud_score", "Fraud Score"),
        ("h_index", "h-index"),
        ("citation_count", "Citations"),
        ("publication_count", "Publications"),
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
            cols[i].metric(label, str(curr_val or "—"))

    # Algorithm version warning
    prev_algo = previous.get("algorithm_version", "?")
    curr_algo = latest.get("algorithm_version", "?")
    if prev_algo != curr_algo:
        st.warning(f"Algorithm version changed: {prev_algo} → {curr_algo}")


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
        st.error("Could not connect to database.")
        return []


def _show_single(snapshot: dict):
    """Display a single snapshot."""
    for key in ("fraud_score", "h_index", "citation_count", "publication_count"):
        val = snapshot.get(key, snapshot.get("metrics", {}).get(key, "—"))
        st.write(f"**{key}**: {val}")


def _render_timeline(snapshots: list[dict]):
    """Render a score timeline chart."""
    try:
        import plotly.graph_objects as go

        dates = [(s.get("snapshot_date") or s.get("created_at") or "")[:10] for s in reversed(snapshots)]
        scores = [s.get("fraud_score", 0) for s in reversed(snapshots)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers", name="Fraud Score"))
        fig.update_layout(
            title="Fraud Score Over Time",
            xaxis_title="Date",
            yaxis_title="Score",
            yaxis={"range": [0, 1]},
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("Plotly required for timeline chart.")

    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()
