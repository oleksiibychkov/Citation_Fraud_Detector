"""Snapshot comparison — time series and delta charts for watchlist authors."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t


def render():
    """Render the snapshot comparison page."""
    st.header(t("dashboard.compare_header"))

    author_id = st.number_input(t("dashboard.author_db_id"), min_value=1, step=1)
    num_snapshots = st.slider(t("dashboard.snapshot_count"), 2, 20, 5)

    if not st.button(t("dashboard.compare_btn")):
        return

    snapshots = _load_snapshots(author_id, num_snapshots)

    if not snapshots:
        st.info(t("dashboard.no_snapshots_found"))
        return

    if len(snapshots) < 2:
        st.warning(t("dashboard.single_snapshot_warning"))
        _show_single(snapshots[0])
        from cfd.dashboard.disclaimer import render_disclaimer
        render_disclaimer()
        return

    # Timeline chart
    st.subheader(t("dashboard.score_dynamics"))
    _render_timeline(snapshots)

    # Change table
    st.subheader(t("dashboard.latest_vs_previous"))
    latest = snapshots[0]
    previous = snapshots[1]

    metric_keys = ["fraud_score", "h_index", "citation_count", "publication_count"]
    metrics = [(k, t(f"compare_metrics.{k}")) for k in metric_keys]

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

    # Algorithm version change warning
    prev_algo = previous.get("algorithm_version", "?")
    curr_algo = latest.get("algorithm_version", "?")
    if prev_algo != curr_algo:
        st.warning(t("dashboard.algo_version_changed", prev=prev_algo, curr=curr_algo))

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
        st.error(t("dashboard.db_connect_error"))
        return []


def _show_single(snapshot: dict):
    """Display a single snapshot."""
    metric_keys = ["fraud_score", "h_index", "citation_count", "publication_count"]
    for key in metric_keys:
        label = t(f"compare_metrics.{key}")
        val = snapshot.get(key, snapshot.get("metrics", {}).get(key, "\u2014"))
        st.write(f"**{label}**: {val}")


def _render_timeline(snapshots: list[dict]):
    """Render a score timeline chart."""
    try:
        import plotly.graph_objects as go

        dates = [(s.get("snapshot_date") or s.get("created_at") or "")[:10] for s in reversed(snapshots)]
        scores = [s.get("fraud_score", 0) for s in reversed(snapshots)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers", name=t("dashboard.activity_score")))
        fig.update_layout(
            title=t("dashboard.score_dynamics_title"),
            xaxis_title=t("dashboard.date_axis"),
            yaxis_title=t("dashboard.score_axis"),
            yaxis={"range": [0, 1]},
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning(t("dashboard.plotly_required"))
