"""Налаштування — регулювання порогових значень індикаторів."""

from __future__ import annotations

import streamlit as st

from cfd.config.settings import Settings

# (field_name, label_ua, min_val, max_val, step, format_str_or_None_for_int)
_THRESHOLD_GROUPS: dict[str, list[tuple]] = {
    "Базові індикатори": [
        ("scr_warn_threshold", "SCR: поріг попередження", 0.01, 1.0, 0.01, "%.2f"),
        ("scr_high_threshold", "SCR: високий поріг", 0.01, 1.0, 0.01, "%.2f"),
        ("mcr_threshold", "MCR: поріг взаємного цитування", 0.01, 1.0, 0.01, "%.2f"),
        ("cb_threshold", "CB: поріг цитатного вузького горла", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "Темпоральні індикатори": [
        ("ta_z_threshold", "TA/HTA: поріг Z-оцінки", 0.5, 10.0, 0.1, "%.1f"),
        ("cv_threshold", "CV: поріг швидкості цитування", 0.5, 20.0, 0.5, "%.1f"),
        ("cv_window_months", "CV: вікно аналізу (місяці)", 6, 120, 1, None),
        ("sbd_beauty_threshold", "SBD: поріг краси (Beauty coefficient)", 10.0, 500.0, 10.0, "%.0f"),
        ("sbd_suspicious_threshold", "SBD: поріг підозрілості", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "Мережеві індикатори": [
        ("rla_threshold", "RLA: поріг аномалії списку літератури", 0.01, 1.0, 0.01, "%.2f"),
        ("gic_threshold", "GIC: поріг географічної кластеризації", 0.01, 1.0, 0.01, "%.2f"),
        ("eigenvector_threshold", "Eigenvector: поріг центральності", 0.01, 1.0, 0.01, "%.2f"),
        ("betweenness_threshold", "Betweenness: поріг посередництва", 0.01, 1.0, 0.01, "%.2f"),
        ("pagerank_threshold", "PageRank: поріг", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "Спільноти та кліки": [
        ("community_density_ratio_threshold", "Поріг щільності спільноти", 0.5, 10.0, 0.1, "%.1f"),
        ("min_community_size", "Мінімальний розмір спільноти", 2, 20, 1, None),
        ("min_clique_size", "Мінімальний розмір кліки", 2, 10, 1, None),
        ("cantelli_z_threshold", "Кантеллі: поріг Z", 0.5, 10.0, 0.1, "%.1f"),
        ("mutual_mcr_threshold", "Поріг MCR для взаємного графа", 0.01, 1.0, 0.01, "%.2f"),
    ],
    "Розширені індикатори": [
        ("ssd_similarity_threshold", "SSD: поріг схожості абстрактів", 0.1, 1.0, 0.01, "%.2f"),
        ("ssd_interval_days", "SSD: інтервал (дні)", 7, 365, 1, None),
        ("cc_per_paper_threshold", "CC: поріг самоцитування на статтю", 0.01, 1.0, 0.01, "%.2f"),
        ("ana_single_paper_coauthor_threshold", "ANA: поріг одноразових співавторів", 0.01, 1.0, 0.01, "%.2f"),
        ("pb_k_neighbors", "PB: кількість k-сусідів", 3, 50, 1, None),
        ("pb_min_peers", "PB: мін. кількість пірів", 1, 20, 1, None),
        ("cpc_divergence_threshold", "CPC: поріг розбіжності", 0.01, 1.0, 0.01, "%.2f"),
        ("ctx_independent_threshold", "CTX: мін. незалежних індикаторів", 1, 10, 1, None),
    ],
}


def render():
    """Render the settings page."""
    st.header("Налаштування")
    st.caption(
        "Регулювання порогових значень індикаторів. "
        "Зміни застосовуються при повторному аналізі на сторінці «Досьє автора»."
    )

    defaults = Settings()

    if "threshold_overrides" not in st.session_state:
        st.session_state["threshold_overrides"] = {}

    overrides = st.session_state["threshold_overrides"]
    changed_count = 0

    for group_name, fields in _THRESHOLD_GROUPS.items():
        st.subheader(group_name)
        cols = st.columns(2)
        for idx, field_def in enumerate(fields):
            field_name, label, min_val, max_val, step, fmt = field_def
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
        if st.button("Скинути до стандартних"):
            st.session_state["threshold_overrides"] = {}
            st.rerun()
    with col2:
        if overrides:
            st.warning(f"Змінено параметрів: {len(overrides)}")
        else:
            st.success("Всі параметри стандартні")
