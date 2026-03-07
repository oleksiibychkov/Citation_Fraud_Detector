"""Author dossier — full analysis with 4 visualizations."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t
from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}


def _get_indicator_info(name: str) -> tuple[str, str]:
    """Get indicator name and description from locale."""
    info = t(f"indicator_info.{name}")
    if isinstance(info, list) and len(info) >= 2:
        return info[0], info[1]
    return name, ""


def _get_effective_settings(overrides: dict | None = None):
    """Build Settings with optional overrides from session_state."""
    from cfd.config.settings import Settings
    settings = Settings()
    if overrides:
        try:
            settings = settings.model_copy(update=overrides)
        except Exception:
            pass
    return settings


def render():
    """Render the author dossier page."""
    st.header(t("dashboard.dossier_header"))

    # Input form (pre-fill from session state)
    col1, col2, col3 = st.columns(3)
    with col1:
        author_name = st.text_input(
            t("dashboard.author_surname"),
            value=st.session_state.get("dossier_author_name", ""),
        )
    with col2:
        scopus_id = st.text_input(
            t("dashboard.scopus_id"),
            value=st.session_state.get("dossier_scopus_id", ""),
        )
    with col3:
        orcid = st.text_input(
            t("dashboard.orcid"),
            value=st.session_state.get("dossier_orcid", ""),
        )

    # Scopus only available with API key
    from cfd.config.settings import Settings as _Settings

    _s = _Settings()
    sources = ["openalex", "auto"]
    if _s.scopus_api_key:
        sources.append("scopus")
    source = st.selectbox(t("dashboard.data_source"), sources)

    # --- Buttons row ---
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        analyze_clicked = st.button(t("dashboard.analyze_btn"))
    with btn_col2:
        has_cached = "dossier_author_data" in st.session_state and st.session_state["dossier_author_data"] is not None
        reanalyze_clicked = st.button(t("dashboard.reanalyze_btn"), disabled=not has_cached)

    overrides = st.session_state.get("threshold_overrides", {})

    # Show override info
    if has_cached and overrides:
        st.info(t("dashboard.overrides_info", count=len(overrides)))

    # --- Handle "Analyze" ---
    if analyze_clicked:
        if not author_name:
            st.error(t("dashboard.surname_required"))
            return
        if not scopus_id and not orcid:
            st.error(t("dashboard.id_required"))
            return

        with st.spinner(t("dashboard.analyzing_spinner")):
            result, author_data, pipeline = _run_analysis(author_name, scopus_id, orcid, source)

        if result is None:
            st.error(t("dashboard.analysis_failed"))
            return

        # Cache in session state
        st.session_state["dossier_result"] = result
        st.session_state["dossier_author_data"] = author_data
        st.session_state["dossier_pipeline"] = pipeline
        st.session_state["dossier_author_name"] = author_name
        st.session_state["dossier_scopus_id"] = scopus_id
        st.session_state["dossier_orcid"] = orcid

    # --- Handle "Re-analyze" ---
    if reanalyze_clicked:
        cached_data = st.session_state.get("dossier_author_data")
        pipeline = st.session_state.get("dossier_pipeline")
        if cached_data and pipeline:
            with st.spinner(t("dashboard.reanalyze_spinner")):
                try:
                    new_result = pipeline.analyze_from_data(
                        cached_data,
                        settings_overrides=overrides or None,
                    )
                    st.session_state["dossier_result"] = new_result
                except Exception as e:
                    st.error(t("dashboard.reanalyze_error", error=str(e)))
        else:
            st.warning(t("dashboard.reanalyze_first"))

    # --- Display results if available ---
    result = st.session_state.get("dossier_result")
    author_data = st.session_state.get("dossier_author_data")

    if result is None:
        return

    effective_settings = _get_effective_settings(overrides)

    # Data source disclaimer
    api_used = getattr(result.author_profile, "source_api", source) or source
    if api_used == "openalex":
        st.warning(t("dashboard.data_source_warning"))

    # Section 1: Author Profile
    st.subheader(t("dashboard.author_profile"))
    profile = result.author_profile
    info_cols = st.columns(4)
    info_cols[0].metric(t("dashboard.name_label"), profile.full_name or author_name)
    info_cols[1].metric(t("dashboard.h_index_label"), profile.h_index if profile.h_index is not None else "\u2014")
    info_cols[2].metric(t("dashboard.publications_label"), profile.publication_count if profile.publication_count is not None else "\u2014")
    info_cols[3].metric(t("dashboard.citations_label"), profile.citation_count if profile.citation_count is not None else "\u2014")

    # Section 2: Publication Activity Score
    st.subheader(t("dashboard.score_header"))
    level = result.confidence_level or "normal"
    if level not in VALID_LEVELS:
        level = "normal"
    color = LEVEL_COLORS.get(level, "#999999")
    level_label = t(f"level_labels.{level}")
    st.markdown(
        f"<h2 style='color:{color}'>{result.fraud_score:.4f} \u2014 {level_label}</h2>",
        unsafe_allow_html=True,
    )

    # Section 3: Indicators with descriptions and thresholds
    st.subheader(t("dashboard.indicators_header"))
    _render_indicators(result, effective_settings)

    # Section 4: Warnings
    if result.warnings:
        st.subheader(t("dashboard.warnings_header"))
        for w in result.warnings:
            st.warning(w)

    # Section 5: Visualizations
    st.subheader(t("dashboard.viz_header"))
    _render_visualizations(author_data, result)

    # Section 6: Conclusion
    _render_conclusion(result, level, color, effective_settings)


def _render_indicators(result, effective_settings):
    """Render indicators with threshold information."""
    from cfd.graph.scoring import get_trigger_threshold

    triggered = set(result.triggered_indicators)
    triggered_details = []
    normal_details = []

    for ind in result.indicators:
        name = ind.indicator_type
        value = ind.value
        is_triggered = name in triggered
        full_name, description = _get_indicator_info(name)
        threshold = get_trigger_threshold(name, effective_settings)

        entry = (name, full_name, value, description, threshold, is_triggered, ind)
        if is_triggered:
            triggered_details.append(entry)
        else:
            normal_details.append(entry)

    # Triggered (suspicious) indicators first
    if triggered_details:
        st.markdown(f"#### \u26a0\ufe0f {t('dashboard.triggered_indicators_header')}")
        for code, full_name, value, description, threshold, _, ind in triggered_details:
            with st.expander(f"\u26a0\ufe0f **{code}** ({full_name}): {value:.4f}", expanded=True):
                _render_threshold_line(code, value, threshold, ind, is_triggered=True)
                st.markdown(description)

    # Normal indicators (collapsed)
    if normal_details:
        st.markdown(f"#### \u2705 {t('dashboard.normal_indicators_header')}")
        for code, full_name, value, description, threshold, _, ind in normal_details:
            with st.expander(f"\u2705 **{code}** ({full_name}): {value:.4f}"):
                _render_threshold_line(code, value, threshold, ind, is_triggered=False)
                st.markdown(description)


def _render_threshold_line(code: str, value: float, threshold: float, ind, *, is_triggered: bool):
    """Render the value/threshold comparison line for an indicator."""
    status_icon = f"\u26a0\ufe0f {t('dashboard.exceeded')}" if is_triggered else f"\u2705 {t('dashboard.within_norm')}"

    # TA and HTA compare z-score from details, not value
    if code in ("TA", "HTA"):
        z_score = ind.details.get("max_z_score", 0)
        st.markdown(
            f"**{t('dashboard.value_label')}:** {value:.4f} (Z-score: {z_score:.2f}) | "
            f"**{t('dashboard.z_score_threshold_label')}:** {threshold:.2f} | {status_icon}"
        )
    else:
        st.markdown(
            f"**{t('dashboard.value_label')}:** {value:.4f} | **{t('dashboard.threshold_label')}:** {threshold:.4f} | {status_icon}"
        )


def _render_conclusion(result, level, color, effective_settings):
    """Render a detailed conclusion about the analysis."""
    from cfd.graph.scoring import (
        TIER1_HARD_EVIDENCE,
        TIER2_CONTEXTUAL,
        TIER3_DYNAMIC,
        get_trigger_threshold,
    )

    st.subheader(t("dashboard.conclusion_header"))

    triggered = result.triggered_indicators
    total = len(result.indicators)
    triggered_count = len(triggered)
    score = result.fraud_score

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric(t("dashboard.indicators_analyzed"), total)
    col2.metric(t("dashboard.indicators_triggered"), triggered_count)
    col3.metric(t("dashboard.activity_score"), f"{score:.4f}")

    # Verdict
    verdict = t(f"level_labels.{level}")

    st.markdown(
        f"### {t('dashboard.verdict_label')}: <span style='color:{color}'>{verdict}</span>",
        unsafe_allow_html=True,
    )

    # Extended conclusion
    conclusion = t(f"level_conclusions.{level}")
    st.markdown(conclusion)

    # Confidence level explanation
    if triggered:
        _render_confidence_explanation(triggered, level)

    # Triggered indicators list with thresholds
    if triggered:
        st.markdown(f"**{t('dashboard.triggered_list_header')}**")
        for code in triggered:
            full_name, _ = _get_indicator_info(code)
            value = 0.0
            for ind in result.indicators:
                if ind.indicator_type == code:
                    value = ind.value
                    break
            threshold = get_trigger_threshold(code, effective_settings)
            st.markdown(f"- **{code}** ({full_name}): {value:.4f} ({t('dashboard.threshold_label')}: {threshold:.4f})")

    # Disclaimer
    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()


def _render_confidence_explanation(triggered: list[str], level: str):
    """Render a textual explanation of why the confidence level was assigned."""
    from cfd.graph.scoring import TIER1_HARD_EVIDENCE, TIER2_CONTEXTUAL, TIER3_DYNAMIC

    tier1 = [ti for ti in triggered if ti in TIER1_HARD_EVIDENCE]
    tier2 = [ti for ti in triggered if ti in TIER2_CONTEXTUAL]
    tier3 = [ti for ti in triggered if ti in TIER3_DYNAMIC]

    lines = []

    if tier1:
        names = ", ".join(f"**{ti}**" for ti in tier1)
        lines.append(t("confidence_explanation.tier1_found", names=names))

    if len(tier2) >= 4:
        names = ", ".join(f"**{ti}**" for ti in tier2)
        lines.append(t("confidence_explanation.tier2_many", count=len(tier2), names=names))
    elif len(tier2) >= 3:
        names = ", ".join(f"**{ti}**" for ti in tier2)
        lines.append(t("confidence_explanation.tier2_several", count=len(tier2), names=names))
    elif tier2:
        names = ", ".join(f"**{ti}**" for ti in tier2)
        lines.append(t("confidence_explanation.tier2_few", names=names))

    if len(tier3) >= 2:
        names = ", ".join(f"**{ti}**" for ti in tier3)
        lines.append(t("confidence_explanation.tier3_many", names=names))
    elif tier3:
        names = ", ".join(f"**{ti}**" for ti in tier3)
        lines.append(t("confidence_explanation.tier3_few", names=names))

    if not lines:
        return

    st.markdown("---")
    st.markdown(f"**{t('dashboard.confidence_explanation_header')}**")
    for line in lines:
        st.markdown(f"- {line}")


def _run_analysis(author_name, scopus_id, orcid, source):
    """Run the analysis pipeline. Returns (result, author_data, pipeline)."""
    try:
        from cfd.cli.main import _build_pipeline, _build_strategy
        from cfd.config.settings import Settings

        settings = Settings()
        # Apply threshold overrides from session state
        overrides = st.session_state.get("threshold_overrides", {})
        if overrides:
            try:
                settings = settings.model_copy(update=overrides)
            except Exception:
                st.warning(t("dashboard.settings_caption"))

        strategy = _build_strategy(source, settings)
        pipeline = _build_pipeline(strategy, settings)

        # Collect data once
        author_data = strategy.collect(
            author_name, scopus_id=scopus_id or None, orcid=orcid or None,
        )

        # Run analysis on collected data (avoids double API call)
        result = pipeline.analyze_from_data(author_data, settings_overrides=overrides or None)

        return result, author_data, pipeline
    except Exception as e:
        st.error(f"{t('error.api_error', message=str(e))}")
        return None, None, None


def _render_visualizations(author_data, result):
    """Render all 4 visualization types."""
    tab1, tab2, tab3, tab4 = st.tabs([
        t("dashboard.tab_network"),
        t("dashboard.tab_timeline"),
        t("dashboard.tab_heatmap"),
        t("dashboard.tab_spikes"),
    ])

    try:
        from cfd.visualization.heatmap import build_mutual_heatmap
        from cfd.visualization.network import build_network_figure
        from cfd.visualization.temporal import build_ht_nt_figure, build_spike_chart

        with tab1:
            fig = build_network_figure(author_data, result)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig = build_ht_nt_figure(author_data)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            fig = build_mutual_heatmap(author_data)
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            fig = build_spike_chart(author_data, result)
            st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning(t("dashboard.viz_import_error"))
    except Exception as e:
        st.warning(t("dashboard.viz_build_error", error=str(e)))
