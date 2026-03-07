"""Settings — adjust indicator threshold values."""

from __future__ import annotations

import streamlit as st

from cfd.config.settings import Settings
from cfd.i18n.translator import t

# (field_name, min_val, max_val, step, format_str_or_None_for_int)
_THRESHOLD_GROUPS: dict[str, list[tuple]] = {
    "basic": [
        ("scr_warn_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("scr_high_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("mcr_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("cb_threshold", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "temporal": [
        ("ta_z_threshold", 0.5, 10.0, 0.1, "%.1f"),
        ("cv_threshold", 0.5, 20.0, 0.5, "%.1f"),
        ("cv_window_months", 6, 120, 1, None),
        ("sbd_beauty_threshold", 10.0, 500.0, 10.0, "%.0f"),
        ("sbd_suspicious_threshold", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "network": [
        ("rla_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("gic_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("eigenvector_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("betweenness_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("pagerank_threshold", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "communities": [
        ("community_density_ratio_threshold", 0.5, 10.0, 0.1, "%.1f"),
        ("min_community_size", 2, 20, 1, None),
        ("min_clique_size", 2, 10, 1, None),
        ("cantelli_z_threshold", 0.5, 10.0, 0.1, "%.1f"),
        ("mutual_mcr_threshold", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "advanced": [
        ("ssd_similarity_threshold", 0.1, 1.0, 0.01, "%.2f"),
        ("ssd_interval_days", 7, 365, 1, None),
        ("cc_per_paper_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("ana_single_paper_coauthor_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("pb_k_neighbors", 3, 50, 1, None),
        ("pb_min_peers", 1, 20, 1, None),
        ("cpc_divergence_threshold", 0.01, 1.0, 0.01, "%.2f"),
        ("ctx_independent_threshold", 1, 10, 1, None),
    ],
}


def render():
    """Render the settings page."""
    st.header(t("dashboard.settings_header"))
    st.caption(t("dashboard.settings_caption"))

    defaults = Settings()

    if "threshold_overrides" not in st.session_state:
        st.session_state["threshold_overrides"] = {}

    overrides = st.session_state["threshold_overrides"]
    changed_count = 0

    for group_key, fields in _THRESHOLD_GROUPS.items():
        st.subheader(t(f"settings_groups.{group_key}"))
        cols = st.columns(2)
        for idx, field_def in enumerate(fields):
            field_name, min_val, max_val, step, fmt = field_def
            label = t(f"settings_labels.{field_name}")
            default_val = getattr(defaults, field_name)
            current = overrides.get(field_name, default_val)

            with cols[idx % 2]:
                is_int = fmt is None
                if is_int:
                    new_val = st.number_input(
                        label,
                        min_value=int(min_val),
                        max_value=int(max_val),
                        value=int(current),
                        step=int(step),
                        key=f"setting_{field_name}",
                    )
                else:
                    new_val = st.number_input(
                        label,
                        min_value=float(min_val),
                        max_value=float(max_val),
                        value=float(current),
                        step=float(step),
                        format=fmt,
                        key=f"setting_{field_name}",
                    )

                if is_int:
                    is_changed = int(new_val) != int(default_val)
                else:
                    is_changed = abs(float(new_val) - float(default_val)) > 1e-9

                if is_changed:
                    overrides[field_name] = int(new_val) if is_int else float(new_val)
                    changed_count += 1
                elif field_name in overrides:
                    del overrides[field_name]

    # Summary and reset
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("dashboard.reset_defaults")):
            st.session_state["threshold_overrides"] = {}
            st.rerun()
    with col2:
        if overrides:
            st.warning(t("dashboard.params_changed", count=len(overrides)))
        else:
            st.success(t("dashboard.all_defaults"))
