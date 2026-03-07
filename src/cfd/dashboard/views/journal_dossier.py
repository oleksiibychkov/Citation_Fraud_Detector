"""Journal dossier — citation manipulation analysis for scientific journals."""

from __future__ import annotations

import streamlit as st

from cfd.i18n.translator import t
from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}


def _get_journal_indicator_info(name: str) -> tuple[str, str]:
    """Get journal indicator name and description from locale."""
    info = t(f"journal_indicator_info.{name}")
    if isinstance(info, list) and len(info) >= 2:
        return info[0], info[1]
    return name, ""


def render():
    """Render the journal dossier page."""
    st.header(t("journal.header"))
    st.caption(t("journal.caption"))

    # Input form
    col1, col2 = st.columns(2)
    with col1:
        journal_name = st.text_input(
            t("journal.name_label"),
            value=st.session_state.get("journal_name", ""),
        )
    with col2:
        issn = st.text_input(
            t("journal.issn_label"),
            value=st.session_state.get("journal_issn", ""),
            placeholder="1234-5678",
        )

    analyze_clicked = st.button(t("journal.analyze_btn"))

    if analyze_clicked:
        if not journal_name and not issn:
            st.error(t("journal.input_required"))
            return

        with st.spinner(t("journal.analyzing_spinner")):
            result = _run_journal_analysis(journal_name, issn)

        if result is None:
            return

        st.session_state["journal_result"] = result
        st.session_state["journal_name"] = journal_name
        st.session_state["journal_issn"] = issn

    # Display results
    result = st.session_state.get("journal_result")
    if result is None:
        return

    if result.status == "insufficient_data":
        st.warning(result.warnings[0] if result.warnings else t("journal.no_data"))
        return

    # Profile section
    st.subheader(t("journal.profile_header"))
    profile = result.profile
    cols = st.columns(4)
    cols[0].metric(t("journal.name_metric"), profile.display_name)
    cols[1].metric(t("journal.h_index_metric"), profile.h_index if profile.h_index is not None else "\u2014")
    cols[2].metric(t("journal.works_metric"), profile.works_count)
    cols[3].metric(t("journal.citations_metric"), profile.cited_by_count)

    # Extra info
    info_cols = st.columns(4)
    info_cols[0].metric(t("journal.publisher_metric"), profile.publisher or "\u2014")
    info_cols[1].metric(t("journal.type_metric"), profile.type or "\u2014")
    info_cols[2].metric(t("journal.oa_metric"), "Yes" if profile.is_oa else "No")
    info_cols[3].metric(t("journal.country_metric"), profile.country_code or "\u2014")

    # Score
    st.subheader(t("journal.score_header"))
    level = result.confidence_level or "normal"
    if level not in VALID_LEVELS:
        level = "normal"
    color = LEVEL_COLORS.get(level, "#999999")
    level_label = t(f"level_labels.{level}")
    st.markdown(
        f"<h2 style='color:{color}'>{result.fraud_score:.4f} \u2014 {level_label}</h2>",
        unsafe_allow_html=True,
    )

    # Indicators
    st.subheader(t("journal.indicators_header"))
    _render_journal_indicators(result)

    # Warnings
    if result.warnings:
        st.subheader(t("journal.warnings_header"))
        for w in result.warnings:
            st.warning(w)

    # Conclusion
    _render_journal_conclusion(result, level, color)


def _render_journal_indicators(result):
    """Render journal indicators with threshold info."""
    from cfd.analysis.journal_pipeline import get_journal_trigger_threshold

    triggered = set(result.triggered_indicators)
    triggered_details = []
    normal_details = []

    for ind in result.indicators:
        name = ind.indicator_type
        value = ind.value
        is_triggered = name in triggered
        full_name, description = _get_journal_indicator_info(name)
        threshold = get_journal_trigger_threshold(name)

        entry = (name, full_name, value, description, threshold, is_triggered)
        if is_triggered:
            triggered_details.append(entry)
        else:
            normal_details.append(entry)

    if triggered_details:
        st.markdown(f"#### \u26a0\ufe0f {t('journal.triggered_header')}")
        for code, full_name, value, description, threshold, _ in triggered_details:
            with st.expander(f"\u26a0\ufe0f **{code}** ({full_name}): {value:.4f}", expanded=True):
                st.markdown(
                    f"**{t('dashboard.value_label')}:** {value:.4f} | "
                    f"**{t('dashboard.threshold_label')}:** {threshold:.4f} | "
                    f"\u26a0\ufe0f {t('dashboard.exceeded')}"
                )
                st.markdown(description)

    if normal_details:
        st.markdown(f"#### \u2705 {t('journal.normal_header')}")
        for code, full_name, value, description, threshold, _ in normal_details:
            with st.expander(f"\u2705 **{code}** ({full_name}): {value:.4f}"):
                st.markdown(
                    f"**{t('dashboard.value_label')}:** {value:.4f} | "
                    f"**{t('dashboard.threshold_label')}:** {threshold:.4f} | "
                    f"\u2705 {t('dashboard.within_norm')}"
                )
                st.markdown(description)


def _render_journal_conclusion(result, level, color):
    """Render conclusion section."""
    st.subheader(t("journal.conclusion_header"))

    triggered = result.triggered_indicators
    total = len(result.indicators)

    col1, col2, col3 = st.columns(3)
    col1.metric(t("dashboard.indicators_analyzed"), total)
    col2.metric(t("dashboard.indicators_triggered"), len(triggered))
    col3.metric(t("journal.manipulation_score"), f"{result.fraud_score:.4f}")

    verdict = t(f"level_labels.{level}")
    st.markdown(
        f"### {t('dashboard.verdict_label')}: <span style='color:{color}'>{verdict}</span>",
        unsafe_allow_html=True,
    )

    conclusion = t(f"journal_conclusions.{level}")
    st.markdown(conclusion)

    if triggered:
        st.markdown(f"**{t('journal.triggered_list')}**")
        from cfd.analysis.journal_pipeline import get_journal_trigger_threshold
        for code in triggered:
            full_name, _ = _get_journal_indicator_info(code)
            value = 0.0
            for ind in result.indicators:
                if ind.indicator_type == code:
                    value = ind.value
                    break
            threshold = get_journal_trigger_threshold(code)
            st.markdown(f"- **{code}** ({full_name}): {value:.4f} ({t('dashboard.threshold_label')}: {threshold:.4f})")

    from cfd.dashboard.disclaimer import render_disclaimer
    render_disclaimer()


def _run_journal_analysis(journal_name: str, issn: str):
    """Run journal analysis pipeline."""
    try:
        from cfd.analysis.journal_pipeline import analyze_journal
        from cfd.config.settings import Settings
        from cfd.data.http_client import CachedHttpClient

        settings = Settings()
        http_client = CachedHttpClient(
            rate_limiters={"openalex": settings.openalex_requests_per_second},
            max_retries=settings.max_retries,
        )

        result = analyze_journal(
            journal_name,
            issn=issn or None,
            http_client=http_client,
        )
        return result
    except Exception as e:
        st.error(f"{t('error.api_error', message=str(e))}")
        return None
